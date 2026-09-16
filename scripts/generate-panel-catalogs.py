#!/usr/bin/env python3
"""Generate panel submission packages from public defaults, never the private .env."""
import argparse
import base64
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


def yaml_text(value, indent=0):
    """Emit the limited YAML the Dokploy blueprint needs: plain keys, quoted strings, ints, lists, maps."""
    pad = '  ' * indent
    if isinstance(value, dict):
        if not value: return '{}\n'
        return ''.join(f"{pad}{key}:" + ('\n' if isinstance(item, (dict, list)) and item else ' ')
                       + yaml_text(item, indent + 1) for key, item in value.items())
    if isinstance(value, list):
        if not value: return '[]\n'
        return ''.join(f"{pad}- " + yaml_text(item, indent + 1) for item in value)
    if isinstance(value, bool): return f"{str(value).lower()}\n"
    if isinstance(value, int): return f"{value}\n"
    return json.dumps(value) + '\n'

def dokploy():
    """Blueprint for the Dokploy template catalog: no proxy labels, hosts derived from four env values."""
    env_keys = ['SERVER_HOST', 'DOMAIN_LIVE', 'DOMAIN_TEST', 'SERVER_HOST_PROTOCOL', 'BOOTSTRAP_ADMIN_EMAIL']
    secrets = [key for key in SECRETS if key != 'REDIS_PASSWORD']
    backend = {}
    for key, value in CONFIG.items():
        if key in EXCLUDED or key in secrets or key.endswith('_HOST') or key in env_keys:
            continue
        backend[key] = value
    backend.update({key: '${' + key + '}' for key in env_keys + secrets})
    host = lambda prefix, domain='SERVER_HOST': f'{prefix}.${{{domain}}}'
    backend.update(DASHBOARD_HOST=host('dashboard'), API_HOST=host('api'), SDK_HOST=host('sdk'),
                   MCP_HOST=host('mcp'), GO_HOST=host('go'), PREVIEW_HOST=host('preview'),
                   LINKS_PROD_HOST=host('links', 'DOMAIN_LIVE'), LINKS_TEST_HOST=host('links', 'DOMAIN_TEST'),
                   REACT_HOST_PROTOCOL='${SERVER_HOST_PROTOCOL}', REACT_HOST=host('dashboard'),
                   PREVIEW_BASE_URL='${SERVER_HOST_PROTOCOL}' + host('preview'),
                   MCP_CONSENT_URL='${SERVER_HOST_PROTOCOL}' + host('dashboard') + '/mcp/authorize',
                   S3_ASSET_PREFIX='${SERVER_HOST_PROTOCOL}' + host('api'),
                   SMTP_DOMAIN='${SERVER_HOST}', MAILER_FROM='Grovs <noreply@${SERVER_HOST}>',
                   RAILS_ENV='production', RAILS_LOG_TO_STDOUT='true', RAILS_SERVE_STATIC_FILES='true',
                   GROVS_SELF_HOSTED='true', GROVS_EE='false', ACTIVE_STORAGE_SERVICE='local',
                   DATABASE_URL='postgres://grovs:${POSTGRES_PASSWORD}@postgres:5432/grovs_production',
                   REDIS_URL='redis://redis:6379/0',
                   CLICKHOUSE_URL='http://grovs:${CLICKHOUSE_PASSWORD}@clickhouse:8123',
                   CLICKHOUSE_DATABASE='grovs_production')
    backend = dict(sorted(backend.items()))
    healthy = lambda *roles: {role: {'condition': 'service_healthy'} for role in roles}
    def sidekiq(*queues):
        return ['bash', '-c', ' '.join(f'bundle exec sidekiq -C config/sidekiq_{q}.yml &' for q in queues) + ' wait -n']
    def app(command, **extra):
        return {'image': IMAGES['web'], 'restart': 'unless-stopped', 'environment': backend,
                'volumes': ['storage:/app/storage'], 'command': command, **extra}
    def links_routing():
        # Dokploy's Domains tab creates the fixed hosts; per-project link hosts need these wildcard routers.
        # Priority 1 keeps Dokploy's own Host() routers ahead of the wildcard when the domains overlap.
        rule = ' || '.join('HostRegexp(`^[a-z0-9-]+\\.${' + key + '}$$`)' for key in ('DOMAIN_LIVE', 'DOMAIN_TEST'))
        service = '${APP_NAME}-links'
        labels = ['traefik.http.services.' + service + '.loadbalancer.server.port=3000']
        for router, entrypoint in ((service, 'web'), (service + '-secure', 'websecure')):
            prefix = 'traefik.http.routers.' + router + '.'
            labels += [prefix + 'rule=' + rule, prefix + 'entrypoints=' + entrypoint,
                       prefix + 'priority=1', prefix + 'service=' + service]
        secure = 'traefik.http.routers.' + service + '-secure.'
        labels += [secure + 'tls=true', secure + 'tls.certresolver=${GROVS_CERT_RESOLVER:-}']
        for index, key in enumerate(('DOMAIN_LIVE', 'DOMAIN_TEST')):
            labels += [f'{secure}tls.domains[{index}].main=${{{key}}}', f'{secure}tls.domains[{index}].sans=*.${{{key}}}']
        return labels
    services = {
        'postgres': {'image': IMAGES['postgres'], 'restart': 'unless-stopped',
                     'environment': {'POSTGRES_USER': 'grovs', 'POSTGRES_PASSWORD': '${POSTGRES_PASSWORD}',
                                     'POSTGRES_DB': 'grovs_production'},
                     'command': ['postgres', '-c', 'max_connections=' + CONFIG['POSTGRES_MAX_CONNECTIONS']],
                     'volumes': ['pg_data:/var/lib/postgresql/data'],
                     'healthcheck': {'test': ['CMD-SHELL', 'pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB'],
                                     'interval': '10s', 'timeout': '5s', 'retries': 10}},
        'redis': {'image': IMAGES['redis'], 'restart': 'unless-stopped',
                  'command': ['redis-server', '--appendonly', 'yes', '--maxmemory-policy', 'noeviction'],
                  'volumes': ['redis_data:/data'],
                  'healthcheck': {'test': ['CMD', 'redis-cli', 'ping'], 'interval': '10s', 'timeout': '5s', 'retries': 10}},
        'clickhouse': {'image': IMAGES['clickhouse'], 'restart': 'unless-stopped',
                       'environment': {'CLICKHOUSE_DB': 'grovs_production', 'CLICKHOUSE_USER': 'grovs',
                                       'CLICKHOUSE_PASSWORD': '${CLICKHOUSE_PASSWORD}'},
                       'volumes': ['clickhouse_data:/var/lib/clickhouse'],
                       'ulimits': {'nofile': {'soft': 262144, 'hard': 262144}},
                       'healthcheck': {'test': ['CMD', 'wget', '--spider', '-q', 'http://localhost:8123/ping'],
                                       'interval': '10s', 'timeout': '5s', 'retries': 30}},
        'migrate': app(['bash', '-c', 'bin/rails db:prepare && bin/rails db:seed && bin/rails clickhouse:setup'],
                       restart='no', depends_on=healthy('postgres', 'redis', 'clickhouse')),
        'web': app(['bundle', 'exec', 'puma', '-b', 'tcp://0.0.0.0:3000'], expose=[3000], labels=links_routing(),
                   depends_on={'migrate': {'condition': 'service_completed_successfully'}},
                   healthcheck={'test': ['CMD', 'curl', '-f', 'http://localhost:3000/up'], 'interval': '10s',
                                'timeout': '5s', 'retries': 30, 'start_period': '60s'}),
        'worker-1': app(sidekiq('scheduler', 'worker', 'batch'), depends_on=healthy('web')),
        'worker-2': app(sidekiq('maintenance', 'device_updates'), depends_on=healthy('web')),
        'dashboard': {'image': IMAGES['dashboard'], 'restart': 'unless-stopped', 'expose': [3000],
                      'environment': {'API_URL': '${SERVER_HOST_PROTOCOL}' + host('api'),
                                      'OAUTH_CLIENT_UID': '${OAUTH_CLIENT_UID}',
                                      'OAUTH_CLIENT_SECRET': '${OAUTH_CLIENT_SECRET}',
                                      'HOSTNAME': '0.0.0.0', 'PORT': '3000'},
                      'depends_on': healthy('web')},
    }
    compose = {'services': services,
               'volumes': {name: {} for name in ('pg_data', 'redis_data', 'clickhouse_data', 'storage')}}

    # URL-safe passwords for connection strings; hex keys everywhere else.
    helpers = {'POSTGRES_PASSWORD': '${password:32}', 'CLICKHOUSE_PASSWORD': '${password:32}',
               'BOOTSTRAP_ADMIN_PASSWORD': '${password:24}', 'OAUTH_CLIENT_UID': '${hash:48}'}
    variables = {'main_domain': '${domain}'}
    variables.update({key.lower(): helpers.get(key, '${hash:64}') for key in secrets})
    env = ['SERVER_HOST=${main_domain}', 'DOMAIN_LIVE=${main_domain}', 'DOMAIN_TEST=test.${main_domain}',
           'SERVER_HOST_PROTOCOL=http://', 'GROVS_CERT_RESOLVER=', 'BOOTSTRAP_ADMIN_EMAIL=admin@${main_domain}']
    env += [f'{key}=${{{key.lower()}}}' for key in secrets]
    domains = [('dashboard', 'dashboard')] + [(prefix, 'web') for prefix in
                                              ('api', 'sdk', 'mcp', 'go', 'preview', 'links', 'links.test')]
    toml = '[variables]\n' + ''.join(f'{k} = "{v}"\n' for k, v in variables.items())
    toml += '\n[config]\nenv = [\n' + ''.join(f'  "{entry}",\n' for entry in env) + ']\n'
    for prefix, service in domains:
        toml += f'\n[[config.domains]]\nserviceName = "{service}"\nport = 3000\nhost = "{prefix}.${{main_domain}}"\n'
    meta = {'id': 'grovs', 'name': 'Grovs', 'version': CONFIG['GROVS_VERSION'],
            'description': 'Self-hosted deep linking, attribution and analytics for mobile and web apps.',
            'logo': 'logo.svg',
            'links': {'github': 'https://github.com/grovs-io/self-host', 'website': 'https://www.grovs.io',
                      'docs': 'https://github.com/grovs-io/self-host/blob/main/deploy/catalogs/dokploy/README.md'},
            'tags': ['analytics', 'developer-tools']}
    return compose, toml, meta


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--check',action='store_true'); args=parser.parse_args()
    ts,meta=easypanel()
    compose,toml,dokploy_meta=dokploy()
    compose_text=yaml_text(compose)
    # Dokploy's Advanced > Import accepts this blob directly, so the template can be tested before it is listed.
    import_blob=base64.b64encode(json.dumps({'compose':compose_text,'config':toml},indent=2).encode()).decode()
    outputs={'deploy/catalogs/dokploy/grovs/docker-compose.yml':compose_text,
             'deploy/catalogs/dokploy/grovs/template.toml':toml,
             'deploy/catalogs/dokploy/import.base64':import_blob+'\n',
             'deploy/catalogs/dokploy/grovs/meta.json':json.dumps(dokploy_meta,indent=2)+'\n',
             'deploy/catalogs/dokploy/grovs/logo.svg':(ROOT/'deploy/catalogs/shared/assets/logo-square-black.svg').read_text(),
             'deploy/catalogs/caprover/grovs.yml':json.dumps(caprover(),indent=2)+'\n',
             'deploy/catalogs/easypanel/grovs/index.ts':ts,
             'deploy/catalogs/easypanel/grovs/meta.yaml':json.dumps(meta,indent=2)+'\n'}
    for name,text in outputs.items():
        path=ROOT/name
        if args.check:
            if not path.exists() or path.read_text()!=text: raise SystemExit(name+' is stale; run scripts/generate-panel-catalogs.py')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

if __name__=='__main__': main()
