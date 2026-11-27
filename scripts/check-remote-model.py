"""Offline profile check by default; one synthetic API smoke only with approval."""
import argparse
import getpass
import json
import os
from pathlib import Path
import sys
import warnings

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from vnlegal.agents.remote_model import read_remote_profile,remote_model_from_profile,OpenAICompatibleJsonModel,configured_credentials,RemoteModelError,list_remote_models,validate_base_url


def configure_credentials(root,base_url):
    root=Path(root).resolve();base_url=validate_base_url(base_url)
    target=root/'config/xai247.credentials.local.json'
    if target.resolve()!=target:raise ValueError('Credential target must not use symlinks')
    if not target.is_relative_to(root):raise ValueError('Credential target must stay in repository')
    if target.exists():raise FileExistsError('Credential file exists; inspect it rather than overwrite')
    if not sys.stdin.isatty():raise ValueError('Run configure in an interactive terminal for hidden input')
    with warnings.catch_warnings():
        warnings.simplefilter('error',getpass.GetPassWarning)
        key=getpass.getpass('API key (hidden): ').strip()
    if not key or '\r' in key or '\n' in key:raise ValueError('Empty or invalid API key')
    target.parent.mkdir(parents=True,exist_ok=True)
    descriptor=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'w') as stream:
        json.dump({'base_url':base_url,'api_key':key},stream,ensure_ascii=False,indent=2)
        stream.write('\n')
    return {'status':'credentials_saved','file':str(target.relative_to(root)),
            'key_displayed':False,'network_called':False}


def preflight(profile):
    # Placeholder is used only for local option validation, never for inference.
    options=dict(profile);options['model_id']=profile.get('model_id') or 'offline-preflight-only'
    OpenAICompatibleJsonModel(**options)
    missing=[]
    if not profile.get('model_id'):missing.append('model_id')
    for key,default in [('base_url_env','XAI247_BASE_URL'),('api_key_env','XAI247_API_KEY')]:
        name=profile.get(key,default)
        if not os.environ.get(name):missing.append(name)
    return {'status':'configuration_present_not_service_verified' if not missing else 'configuration_incomplete',
            'missing':missing,'model_id':profile.get('model_id'),'network_called':False,
            'inference_verified':False,'paid_api_enabled':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['preflight','configure','models','smoke'],nargs='?',default='preflight')
    p.add_argument('--config',default='config/xai247-model.json')
    p.add_argument('--allow-paid-api',action='store_true');p.add_argument('--output')
    p.add_argument('--credentials-file',help='Explicit repository-local JSON file, never printed')
    p.add_argument('--base-url',default='https://xai247.xyz/v1',help='Public endpoint used only by configure')
    args=p.parse_args()
    if args.action=='configure':
        result=configure_credentials(ROOT,args.base_url)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    if args.action=='models':
        profile=read_remote_profile(ROOT,args.config)
        output=(ROOT/args.output).resolve() if args.output else None
        if output is not None:
            if not output.is_relative_to(ROOT):raise ValueError('Output must stay in repository')
            if output.exists():raise FileExistsError('Metadata output exists, do not overwrite')
            output.mkdir(parents=True,exist_ok=False)
        try:
            with configured_credentials(ROOT,profile,args.credentials_file):result=list_remote_models(profile)
        except Exception as exc:
            result={'status':'failed','error_type':type(exc).__name__,'generation_called':False}
            if isinstance(exc,RemoteModelError):result['error_reason']=str(exc)
        if output is not None:
            with (output/'result.json').open('x') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['status']=='catalog_read' else 2
    if args.action=='preflight':
        profile=read_remote_profile(ROOT,args.config)
        with configured_credentials(ROOT,profile,args.credentials_file):result=preflight(profile)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 2 if result['missing'] else 0
    if not args.allow_paid_api:raise ValueError('Smoke requires explicit --allow-paid-api approval')
    if not args.output:raise ValueError('Smoke requires a new output directory')
    output=(ROOT/args.output).resolve()
    if not output.is_relative_to(ROOT):raise ValueError('Output must stay within repository')
    if output.exists():raise FileExistsError('Output exists; inspect it instead of repeating an API call')
    model=remote_model_from_profile(ROOT,args.config,allow_paid_api=True)
    output.mkdir(parents=True,exist_ok=False)
    result={'status':'failed','model_id':model.model_id,'revision':model.revision,
            'identity_attested':False,'scope':'synthetic_connectivity_check_not_legal_quality'}
    try:
        profile={'base_url_env':model.base_url_env,'api_key_env':model.api_key_env}
        with configured_credentials(ROOT,profile,args.credentials_file):
            response=model.generate_json('connectivity_check',{'instruction':'Trả đúng JSON {"status":"ok"} để kiểm tra kết nối, không thêm trường.'})
        if response!={'status':'ok'}:raise ValueError('Smoke contract mismatch')
        result.update(status='passed',response=response)
    except Exception as exc:
        result['error_type']=type(exc).__name__  # Never copy exception bodies/URLs/credentials.
        if isinstance(exc,RemoteModelError):result['error_reason']=str(exc)  # Redacted library-generated reason only.
    result.update(calls_started=model.calls_started,usage=model.usage,client_halted=model.halted)
    with (output/'result.json').open('x') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['status']=='passed' else 2


if __name__=='__main__':raise SystemExit(main())
