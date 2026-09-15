#!/usr/bin/env python3
"""Generate panel submission packages from public defaults, never the private .env."""
import argparse
import importlib.util
import json
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('paas', ROOT / 'scripts/generate-paas.py')
paas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paas)
CONFIG = paas.defaults()
IMAGES = {'postgres': 'postgres:16.10-alpine', 'redis': 'redis:7.4.5-alpine',
          'clickhouse': 'clickhouse/clickhouse-server:25.3.6.56',
          'web': 'ghcr.io/grovs-io/backend:' + CONFIG['GROVS_VERSION'],
          'dashboard': 'ghcr.io/grovs-io/dashboard:' + CONFIG['GROVS_VERSION']}
FIELDS = {
 'appDomain': ('SERVER_HOST', 'App base domain', 'grovs.example.com'),
 'linksDomain': ('DOMAIN_LIVE', 'Production links domain', 'links.example.com'),
 'testDomain': ('DOMAIN_TEST', 'Test links domain', 'test.links.example.com'),
 'adminEmail': ('BOOTSTRAP_ADMIN_EMAIL', 'Administrator email', 'admin@example.com'),
 's3Key': ('AWS_S3_KEY_ID', 'Object storage access key', ''),
 's3Secret': ('AWS_S3_ACCESS_KEY', 'Object storage secret key', ''),
 's3Region': ('AWS_S3_REGION', 'Bucket region', 'us-east-1'),
 's3Bucket': ('AWS_S3_BUCKET', 'Private bucket name', ''),
 's3Endpoint': ('S3_ENDPOINT', 'S3-compatible endpoint (optional)', ''),
}
SECRETS = [k for k, v in CONFIG.items() if v == 'change-me'] + ['REDIS_PASSWORD']
EXCLUDED = {'COMPOSE_PROJECT_NAME', 'GROVS_VERSION', 'ACME_EMAIL', 'PREVIEW_BASE_URL',
            'MCP_CONSENT_URL', 'S3_ASSET_PREFIX', 'SMTP_DOMAIN', 'MAILER_FROM'}
BASE = {k:v for k,v in CONFIG.items() if k not in EXCLUDED and k not in SECRETS
        and not k.endswith('_HOST') and k not in [v[0] for v in FIELDS.values()]}
BASE.update(RAILS_ENV='production', GROVS_SELF_HOSTED='true', GROVS_EE='false',
            RAILS_LOG_TO_STDOUT='true', RAILS_SERVE_STATIC_FILES='true',
            ACTIVE_STORAGE_SERVICE='amazon', CLICKHOUSE_DATABASE='grovs_production', PORT='3000')
SETUP = (ROOT / 'deploy/paas/backend-env.sh').read_text()
# Bound startup waits and use the application gems already present in the image.
WAIT_PG = '''ruby -rpg -e '120.times do
  begin
    PG.connect(ENV.fetch("DATABASE_URL"), connect_timeout: 5).close
    exit 0
  rescue PG::Error
    sleep 5
  end
end
abort "PostgreSQL did not become ready"'
'''
COMMANDS = paas.commands()
COMMANDS['web'] = 'bash -ec ' + shlex.quote(SETUP + '\n' + WAIT_PG + '\n'
    'wait_for_http "http://$CLICKHOUSE_HOST:8123/ping"\n'
    'bin/rails db:prepare\nbin/rails db:seed\nbin/rails clickhouse:setup\n'
    'exec bundle exec puma -b "tcp://0.0.0.0:${PORT:-3000}"')


def caprover():
    ref = lambda k: '$$cap_' + k
    env = dict(BASE)
    env.update({key:ref(key) for key in SECRETS})
    env.update({value[0]: ref(value[0]) for value in FIELDS.values()})
    for key, role in [('POSTGRES_HOST','postgres'),('REDIS_HOST','redis'),('CLICKHOUSE_HOST','clickhouse'),('WEB_HOST','web')]:
        env[key]='srv-captain--$$cap_appname-' + role
    env.update(WEB_PORT='3000', SMTP_DOMAIN=ref('SERVER_HOST'), MAILER_FROM='Grovs <noreply@'+ref('SERVER_HOST')+'>')
    services={}
    def add(role, image, env, volume=None, command=None, public=False):
        s={'image':image,'environment':env,'caproverExtra': {'containerHttpPort':'3000'} if public else {'notExposeAsWebApp':'true'}}
        if volume: s['volumes']=['$$cap_appname-'+role+'-data:'+volume]
        if command: s['command']=shlex.split(command)
        services['$$cap_appname-'+role]=s
    add('postgres',IMAGES['postgres'],{'POSTGRES_DB':'grovs_production','POSTGRES_USER':'grovs','POSTGRES_PASSWORD':ref('POSTGRES_PASSWORD')},'/var/lib/postgresql/data')
    add('redis',IMAGES['redis'],{},'/data', 'redis-server --appendonly yes --maxmemory-policy noeviction --requirepass '+ref('REDIS_PASSWORD'))
    add('clickhouse',IMAGES['clickhouse'],{'CLICKHOUSE_DB':'grovs_production','CLICKHOUSE_USER':'grovs','CLICKHOUSE_PASSWORD':ref('CLICKHOUSE_PASSWORD')},'/var/lib/clickhouse')
    for role in ['web','worker-1','worker-2']:
        add(role,IMAGES['web'],env,command=COMMANDS[role],public=role=='web')
    add('dashboard',IMAGES['dashboard'],{'API_URL':'https://api.'+ref('SERVER_HOST'),'OAUTH_CLIENT_UID':ref('OAUTH_CLIENT_UID'),
        'OAUTH_CLIENT_SECRET':ref('OAUTH_CLIENT_SECRET'),'HOSTNAME':'0.0.0.0','PORT':'3000'},public=True)
    variables=[]
    for _, (key,label,example) in FIELDS.items():
        pattern=r'/^[^\r\n]+$/' if key!='S3_ENDPOINT' else r'/^[^\r\n]*$/'
        if key in ['SERVER_HOST','DOMAIN_LIVE','DOMAIN_TEST']: pattern=r'/^[a-z0-9][a-z0-9.-]*\.[a-z0-9-]+$/'
        variables.append({'id':ref(key),'label':label,'defaultValue':'','description':('Example: '+example if example else label), 'validRegex':pattern})
    for key in SECRETS:
        variables.append({'id':ref(key),'label':key,'defaultValue':'$$cap_gen_random_hex(32)','description':'Generated once and shared by the services. Save this value securely.', 'validRegex':r'/^[a-f0-9]{64}$/'})
    return {'captainVersion':4,'services':services,'caproverOneClickApp':{'displayName':'Grovs Community',
      'isOfficial':True,'description':'Self-hosted deep linking, attribution and analytics for mobile and web apps.',
      'documentation':'https://github.com/grovs-io/self-host/blob/main/deploy/catalogs/caprover/README.md',
      'variables':variables,'instructions':{
       'start':'Requires 4 vCPU / 8 GB RAM, a private S3-compatible bucket, and your own domains. Use one server and one replica of each service. Configure wildcard domains and certificates using the guide. Images: https://github.com/grovs-io/self-host',
       'end':'Read https://github.com/grovs-io/self-host/blob/main/deploy/catalogs/caprover/README.md to attach domains and enable HTTPS before login. Admin credentials are in the web service environment. Preserve volumes and secrets on upgrades; do not reinstall this template over an existing deployment.'}}}


def easypanel():
    constants='\n'.join('const '+k+' = '+json.dumps(v,indent=2)+';' for k,v in [('baseEnv',BASE),('images',IMAGES),('commands',COMMANDS),('secretKeys',SECRETS),('fields', {k:v[0] for k,v in FIELDS.items()})])
    source='''import { Output, Services } from "~templates-utils";
import { Input } from "./meta";

// Use Web Crypto: generated database, OAuth and encryption keys must be unpredictable.
function secret(): string {
  return Array.from(globalThis.crypto.getRandomValues(new Uint8Array(32)))
    .map((byte) => byte.toString(16).padStart(2, "0")).join("");
}
'''+constants+'''
export function generate(input: Input): Output {
  for (const value of Object.values(input)) {
    if (typeof value === "string" && /[\\r\\n]/.test(value)) throw new Error("Values must be a single line");
  }
  const services: Services = [];
  const env: Record<string,string> = { ...baseEnv };
  for (const key of secretKeys) env[key] = secret();
  for (const [field,key] of Object.entries(fields)) env[key] = String(input[field as keyof Input] || "");
  const host = (role: string) => `$(PROJECT_NAME)_${input.servicePrefix}-${role}`;
  Object.assign(env, { POSTGRES_HOST: host("postgres"), REDIS_HOST: host("redis"),
    CLICKHOUSE_HOST: host("clickhouse"), WEB_HOST: host("web"), WEB_PORT: "3000",
    SMTP_DOMAIN: input.appDomain, MAILER_FROM: `Grovs <noreply@${input.appDomain}>` });
  const add = (role: string, image: string, values: Record<string,string>, command?: string, volume?: string) => {
    services.push({ type: "app", data: {
      serviceName: `${input.servicePrefix}-${role}`, source: { type: "image", image },
      env: Object.entries(values).map(([k,v]) => `${k}=${v}`).join("\\n"),
      deploy: { command: command || null, replicas: 1, zeroDowntime: false },
      mounts: volume ? [{ type: "volume", name: "data", mountPath: volume }] : [],
    }});
  };
  add("postgres",images.postgres,{POSTGRES_DB:"grovs_production",POSTGRES_USER:"grovs",POSTGRES_PASSWORD:env.POSTGRES_PASSWORD},undefined,"/var/lib/postgresql/data");
  add("redis",images.redis,{},`redis-server --appendonly yes --maxmemory-policy noeviction --requirepass ${env.REDIS_PASSWORD}`,"/data");
  add("clickhouse",images.clickhouse,{CLICKHOUSE_DB:"grovs_production",CLICKHOUSE_USER:"grovs",CLICKHOUSE_PASSWORD:env.CLICKHOUSE_PASSWORD},undefined,"/var/lib/clickhouse");
  for (const role of ["web","worker-1","worker-2"] as const) add(role,images.web,env,commands[role]);
  add("dashboard",images.dashboard,{API_URL:`https://api.${input.appDomain}`,OAUTH_CLIENT_UID:env.OAUTH_CLIENT_UID,OAUTH_CLIENT_SECRET:env.OAUTH_CLIENT_SECRET,HOSTNAME:"0.0.0.0",PORT:"3000"});
  // Explicit hosts get HTTPS. Wildcard link routing/certificates are configured in the guide.
  const web = services.find(s => s.data.serviceName === `${input.servicePrefix}-web`)!;
  if (web.type === "app") web.data.domains = ["api","sdk","mcp","go","preview"].map(prefix => ({host:`${prefix}.${input.appDomain}`,port:3000,https:true}));
  const dashboard = services[services.length-1];
  if (dashboard.type === "app") dashboard.data.domains = [{host:`dashboard.${input.appDomain}`,port:3000,https:true}];
  return {services};
}
'''
    properties={'servicePrefix': {'type':'string','title':'Service name prefix','default':'grovs','pattern':'^[a-z][a-z0-9-]+$'}}
    for key, (_, label, example) in FIELDS.items():
        properties[key]={'type':'string','title':label,'default':'','description':('Example: '+example if example else label),'pattern':'^[^\\r\\n]*$'}
        if key!='s3Endpoint': properties[key]['minLength']=1
        if key in ['appDomain','linksDomain','testDomain']: properties[key]['pattern']='^[a-z0-9][a-z0-9.-]*\\.[a-z0-9-]+$'
    metadata={'name':'Grovs Community','description':'Self-hosted deep linking, attribution and analytics for mobile and web apps.',
      'instructions':'Requires 4 vCPU / 8 GB RAM and a private S3-compatible bucket. Use one replica per service. Configure wildcard routing and TLS before using project links: https://github.com/grovs-io/self-host/blob/main/deploy/catalogs/easypanel/README.md. Read the generated admin password from the web service environment. Preserve secrets and volumes when upgrading; do not regenerate an existing template.',
      'links':[{'label':label,'url':url} for label,url in [('Website','https://www.grovs.io'),('Documentation','https://www.grovs.io/docs/self-hosting/introduction'),('Github','https://github.com/grovs-io/backend')]],
      'contributors':[{'name':'Grovs','url':'https://github.com/grovs-io'}],
      'changeLog':[{'date':'2026-09-15','description':'Initial submission package'}],
      'schema':{'type':'object','required':[k for k in properties if k!='s3Endpoint'],'properties':properties},
      'benefits':[{'title':'Own your data','description':'Operate deep links and analytics in your own account.'}],
      'features':[{'title':'Deep links and analytics','description':'Create branded links and measure engagement using the Grovs SDKs and dashboard.'}], 'tags':['Analytics','Developer Tools']}
    return source,metadata


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--check',action='store_true'); args=parser.parse_args()
    ts,meta=easypanel()
    outputs={'deploy/catalogs/caprover/grovs.yml':json.dumps(caprover(),indent=2)+'\n',
             'deploy/catalogs/easypanel/grovs/index.ts':ts,
             'deploy/catalogs/easypanel/grovs/meta.yaml':json.dumps(meta,indent=2)+'\n'}
    for name,text in outputs.items():
        path=ROOT/name
        if args.check:
            if not path.exists() or path.read_text()!=text: raise SystemExit(name+' is stale; run scripts/generate-panel-catalogs.py')
        else: path.write_text(text)

if __name__=='__main__': main()
