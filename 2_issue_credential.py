import asyncio
import json
from indy import pool, wallet, did, anoncreds, ledger

pool_name = 'local-pool'
issuer_wallet_config = json.dumps({"id": "issuer_wallet"})
issuer_credentials = json.dumps({"key": "issuer_key"})
holder_wallet_config = json.dumps({"id": "holder_wallet"})
holder_credentials = json.dumps({"key": "holder_key"})

async def main():
    print("========================================")
    print("실습 3 - Step 2: Request & Issue Credential (VC 발급)")
    print("========================================\n")

    # 이전 실습 데이터 불러오기
    try:
        with open('shared_data.json', 'r') as f:
            data = json.load(f)
            cred_def_id = data['cred_def_id']
            issuer_did = data['issuer_did']
    except Exception as e:
        print("[오류] shared_data.json 파일을 찾을 수 없습니다. 1번 스크립트를 먼저 실행하세요.")
        return
    try:
        pool_config = json.dumps({"genesis_txn": "pool_transactions_genesis"})
        await pool.create_pool_ledger_config(config_name=pool_name, config=pool_config)
    except: pass

    pool_handle = await pool.open_pool_ledger(config_name=pool_name, config=None)
    
    # Issuer 및 Holder 지갑 열기
    issuer_wallet = await wallet.open_wallet(issuer_wallet_config, issuer_credentials)
    
    try: await wallet.create_wallet(holder_wallet_config, holder_credentials)
    except: pass
    holder_wallet = await wallet.open_wallet(holder_wallet_config, holder_credentials)

    # Holder의 DID(Master Secret) 생성
    holder_did, _ = await did.create_and_store_my_did(holder_wallet, "{}")
    try:
        master_secret_id = await anoncreds.prover_create_master_secret(holder_wallet, 'master_secret_name')
    except:
        master_secret_id = 'master_secret_name'

    # 원장에서 CredDef 가져오기 (오프체인이 아닌 온체인 정보 활용)
    get_cred_def_req = await ledger.build_get_cred_def_request(holder_did, cred_def_id)
    get_cred_def_res = await ledger.submit_request(pool_handle, get_cred_def_req)
    _, cred_def_json = await ledger.parse_get_cred_def_response(get_cred_def_res)

    print("[*] 원장에서 Credential Definition 획득 완료")

    # 1. Issuer -> Holder: Credential Offer 생성 및 전달 (가정)
    cred_offer_json = await anoncreds.issuer_create_credential_offer(issuer_wallet, cred_def_id)
    print(f"[*] Issuer가 Credential Offer 생성")

    # 2. Holder -> Issuer: Credential Request (VC 요청) 생성 및 전달
    cred_req_json, cred_req_metadata_json = await anoncreds.prover_create_credential_req(
        holder_wallet, holder_did, cred_offer_json, cred_def_json, master_secret_id)
    print(f"[*] Holder가 Credential Request(VC 발급 요청) 생성")

    # 3. Issuer -> Holder: 실제 Credential(VC) 생성 발급
    cred_values = json.dumps({
        "name": {"raw": "홍길동", "encoded": "11394817164528"},
        "degree": {"raw": "Computer Science", "encoded": "123123123"},
        "year": {"raw": "2026", "encoded": "2026"}
    })
    
    cred_json, _, _ = await anoncreds.issuer_create_credential(
        issuer_wallet, cred_offer_json, cred_req_json, cred_values, None, None)
    print(f"[*] Issuer가 유효한 VC(Verifiable Credential)를 생성 발급")

    # 4. Holder: 수령한 VC를 지갑에 안전하게 저장
    cred_id = await anoncreds.prover_store_credential(
        holder_wallet, None, cred_req_metadata_json, cred_json, cred_def_json, None)
    
    print(f"\n[성공] Holder 지갑에 VC(저장 ID: {cred_id})가 저장되었습니다!")

    # 검증 실습을 위해 저장
    with open('shared_holder_data.json', 'w') as f:
        json.dump({'cred_id': cred_id, 'holder_did': holder_did}, f)

    await wallet.close_wallet(issuer_wallet)
    await wallet.close_wallet(holder_wallet)
    await pool.close_pool_ledger(pool_handle)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
