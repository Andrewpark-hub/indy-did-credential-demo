import asyncio
import json
from indy import pool, wallet, anoncreds, ledger, did

pool_name = 'local-pool'
holder_wallet_config = json.dumps({"id": "holder_wallet"})
holder_credentials = json.dumps({"key": "holder_key"})

verifier_wallet_config = json.dumps({"id": "verifier_wallet"})
verifier_credentials = json.dumps({"key": "verifier_key"})

async def main():
    print("========================================")
    print("실습 3 - Step 3: Verify Presentation (VP 검증)")
    print("========================================\n")

    # 이전 실습 데이터 로드
    try:
        with open('shared_data.json', 'r') as f:
            data = json.load(f)
            cred_def_id = data['cred_def_id']
            schema_id = data['schema_id']
    except Exception:
        print("[오류] shared_data.json 파일을 찾을 수 없습니다.")
        return

    try:
        pool_config = json.dumps({"genesis_txn": "pool_transactions_genesis"})
        await pool.create_pool_ledger_config(config_name=pool_name, config=pool_config)
    except: pass

    pool_handle = await pool.open_pool_ledger(config_name=pool_name, config=None)
    holder_wallet = await wallet.open_wallet(holder_wallet_config, holder_credentials)
    
    try: await wallet.create_wallet(verifier_wallet_config, verifier_credentials)
    except: pass
    verifier_wallet = await wallet.open_wallet(verifier_wallet_config, verifier_credentials)
    verifier_did, _ = await did.create_and_store_my_did(verifier_wallet, "{}")

    # 1. Verifier -> Holder: Proof Request (검증 요청) 생성 및 전달
    # "전공(degree)이 Computer Science 인가? 이름은 무엇인가?" 를 확인하는 정책
    proof_request = json.dumps({
        "nonce": "12343242122312411212",
        "name": "Degree-Verification",
        "version": "1.0",
        "requested_attributes": {
            "attr1_referent": {"name": "name", "restrictions": [{"cred_def_id": cred_def_id}]},
            "attr2_referent": {"name": "degree", "restrictions": [{"cred_def_id": cred_def_id}]}
        },
        "requested_predicates": {} # 나이 등 크기 비교 조건이 필요한 경우 사용
    })
    print("[*] Verifier가 Proof Request 생성 (요청 속성: name, degree)")

    # 2. Holder: 지갑을 검색하여 Proof Request 조건에 맞는 VC들을 탐색
    search_handle = await anoncreds.prover_search_credentials_for_proof_req(holder_wallet, proof_request, None)
    
    creds_for_attr1 = await anoncreds.prover_fetch_credentials_for_proof_req(search_handle, 'attr1_referent', 10)
    cred_for_attr1 = json.loads(creds_for_attr1)[0]['cred_info']

    creds_for_attr2 = await anoncreds.prover_fetch_credentials_for_proof_req(search_handle, 'attr2_referent', 10)
    cred_for_attr2 = json.loads(creds_for_attr2)[0]['cred_info']

    await anoncreds.prover_close_credentials_search_for_proof_req(search_handle)

    # 3. Holder -> Verifier: VP(Verifiable Presentation) 생성 및 제출
    requested_credentials = json.dumps({
        "self_attested_attributes": {},
        "requested_attributes": {
            "attr1_referent": {"cred_id": cred_for_attr1['referent'], "revealed": True},
            "attr2_referent": {"cred_id": cred_for_attr2['referent'], "revealed": True}
        },
        "requested_predicates": {}
    })
    
    # VP를 만드는데 필요한 스키마 정보 / 원장 정보 로드
    get_schema_req = await ledger.build_get_schema_request(verifier_did, schema_id)
    get_schema_res = await ledger.submit_request(pool_handle, get_schema_req)
    _, schema_json = await ledger.parse_get_schema_response(get_schema_res)

    get_cred_def_req = await ledger.build_get_cred_def_request(verifier_did, cred_def_id)
    get_cred_def_res = await ledger.submit_request(pool_handle, get_cred_def_req)
    _, cred_def_json = await ledger.parse_get_cred_def_response(get_cred_def_res)

    schemas_json = json.dumps({schema_id: json.loads(schema_json)})
    cred_defs_json = json.dumps({cred_def_id: json.loads(cred_def_json)})

    # VP(Proof) 생성
    proof_json = await anoncreds.prover_create_proof(
        holder_wallet, proof_request, requested_credentials,
        'master_secret_name', schemas_json, cred_defs_json, "{}"
    )
    print("[*] Holder가 자신의 VC를 기반으로 Proof(VP) 생성 및 제출 완료")

    # 4. Verifier: 전달받은 VP를 온체인 데이터(CredDef 등)와 대조하여 암호학적으로 검증
    valid = await anoncreds.verifier_verify_proof(
        proof_request, proof_json, schemas_json, cred_defs_json, "{}", "{}"
    )

    print(f"\n[검증 결과] 온체인 데이터를 활용한 VP 암호학적 검증 매칭 여부: {'성공(True)' if valid else '실패(False)'}")
    
    if valid:
        revealed = json.loads(proof_json)['requested_proof']['revealed_attrs']
        print(f"제공된 정보: 이름 - {revealed['attr1_referent']['raw']}, 전공 - {revealed['attr2_referent']['raw']}")

    await wallet.close_wallet(holder_wallet)
    await wallet.close_wallet(verifier_wallet)
    await pool.close_pool_ledger(pool_handle)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
