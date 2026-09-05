import asyncio
import json
import os
from indy import pool, wallet, did, ledger, anoncreds

pool_name = 'local-pool'
wallet_config = json.dumps({"id": "issuer_wallet"})
wallet_credentials = json.dumps({"key": "issuer_key"})

async def main():
    print("========================================")
    print("실습 3 - Step 1: Issuer Schema & Credential Definition")
    print("========================================\n")

    # 1. Pool & Wallet Setup
    genesis_path = 'pool_transactions_genesis' if os.path.exists('pool_transactions_genesis') else '/workspace/pool_transactions_genesis'
    pool_config = json.dumps({"genesis_txn": genesis_path})
    try:
        await pool.create_pool_ledger_config(config_name=pool_name, config=pool_config)
    except: pass # 이미 존재하면 무시

    pool_handle = await pool.open_pool_ledger(config_name=pool_name, config=None)
    try:
        await wallet.create_wallet(wallet_config, wallet_credentials)
    except: pass # 이미 존재하는 경우 무시
    wallet_handle = await wallet.open_wallet(wallet_config, wallet_credentials)

    # 2. Steward(Trust Anchor) 권한 생성 및 활용
    # von-network의 기본 Steward Seed를 연동하여 Issuer의 DID 등록 권한 확보
    steward_did, _ = await did.create_and_store_my_did(wallet_handle, json.dumps({'seed': '000000000000000000000000Steward1'}))
    
    # Issuer DID 생성
    issuer_did, issuer_verkey = await did.create_and_store_my_did(wallet_handle, "{}")
    print(f"[*] Issuer DID 생성: {issuer_did}")

    # Steward를 통한 Issuer DID 원장 등록 (TRUST_ANCHOR 부여)
    nym_request = await ledger.build_nym_request(submitter_did=steward_did, target_did=issuer_did, ver_key=issuer_verkey, alias=None, role='TRUST_ANCHOR')
    await ledger.sign_and_submit_request(pool_handle=pool_handle, wallet_handle=wallet_handle, submitter_did=steward_did, request_json=nym_request)
    print("[*] Issuer DID가 원장에 Trust Anchor로 등록되었습니다.")

    # 3. Schema 생성 및 원장 등록
    schema_name = 'DegreeSchema'
    schema_version = '1.1'
    schema_attributes = json.dumps(["name", "degree", "year"])
    
    schema_id, schema_json = await anoncreds.issuer_create_schema(issuer_did, schema_name, schema_version, schema_attributes)
    print(f"\n[*] Schema 생성 완료. ID: {schema_id}")
    
    schema_request = await ledger.build_schema_request(issuer_did, schema_json)
    await ledger.sign_and_submit_request(pool_handle, wallet_handle, issuer_did, schema_request)
    print("[*] Schema가 원장에 등록됨.")

    # 원장으로부터 Schema 데이터를 객체로 받아옴 (CredDef 생성을 위해)
    await asyncio.sleep(1)
    get_schema_req = await ledger.build_get_schema_request(issuer_did, schema_id)
    get_schema_res = await ledger.submit_request(pool_handle, get_schema_req)
    _, schema_metadata_json = await ledger.parse_get_schema_response(get_schema_res)

    # 4. Credential Definition 생성 및 원장 등록
    cred_def_id, cred_def_json = await anoncreds.issuer_create_and_store_credential_def(
        wallet_handle, issuer_did, schema_metadata_json, tag='TAG1', signature_type='CL', config_json=json.dumps({"support_revocation": False}))
    print(f"\n[*] Credential Definition 생성 완료. ID: {cred_def_id}")

    cred_def_request = await ledger.build_cred_def_request(issuer_did, cred_def_json)
    await ledger.sign_and_submit_request(pool_handle, wallet_handle, issuer_did, cred_def_request)
    print("[*] Credential Definition이 원장에 등록됨.")

    # 결과 데이터 저장 (다음 실습을 위함)
    with open('shared_data.json', 'w') as f:
        json.dump({'schema_id': schema_id, 'cred_def_id': cred_def_id, 'issuer_did': issuer_did}, f)
    print("\n[성공] shared_data.json에 스키마 및 CredDef 정보가 저장되었습니다.")

    await wallet.close_wallet(wallet_handle)
    await pool.close_pool_ledger(pool_handle)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
