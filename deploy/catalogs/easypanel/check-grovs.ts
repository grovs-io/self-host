import assert from 'node:assert/strict';
import { generate } from './templates/grovs';
import { templateSchema } from './utils/schema';
const input = { servicePrefix:'grovs', appDomain:'grovs.example.com', linksDomain:'links.example.com', testDomain:'test.links.example.com', adminEmail:'admin@example.com', s3Key:'example-key', s3Secret:'example-secret', s3Region:'us-east-1', s3Bucket:'example-bucket', s3Endpoint:'' };
const first = templateSchema.parse(generate(input));
const second = templateSchema.parse(generate(input));
assert.equal(first.services.length,7);
const env = (run:any,name:string) => Object.fromEntries(run.services.find((s:any)=>s.data.serviceName===name).data.env.split('\n').map((l:string)=>{const i=l.indexOf('=');return [l.slice(0,i),l.slice(i+1)]}));
const web=env(first,'grovs-web'), worker=env(first,'grovs-worker-1'), dashboard=env(first,'grovs-dashboard');
for(const key of ['SECRET_KEY_BASE','OAUTH_CLIENT_SECRET','POSTGRES_PASSWORD','ACTIVE_RECORD_ENCRYPTION_PRIMARY_KEY']) {
 assert.match(web[key],/^[0-9a-f]{64}$/);
 assert.equal(web[key],worker[key]);
 assert.notEqual(web[key],env(second,'grovs-web')[key]);
}
assert.equal(web.OAUTH_CLIENT_SECRET,dashboard.OAUTH_CLIENT_SECRET);
assert.equal(web.POSTGRES_PASSWORD,env(first,'grovs-postgres').POSTGRES_PASSWORD);
for(const service of first.services) {
 if(service.type!=='app') throw new Error('Unexpected service');
 assert.equal(service.data.deploy.replicas,1);
 assert.equal(service.data.deploy.zeroDowntime,false);
 if(['grovs-postgres','grovs-redis','grovs-clickhouse'].includes(service.data.serviceName)) {
  assert.equal(service.data.mounts.length,1);
  assert.equal(service.data.domains.length,0);
  assert.equal(service.data.ports.length,0);
 }
}
assert.throws(()=>generate({...input,s3Secret:'value\nINJECT=1'}));
console.log('Grovs: upstream schema, seven services, isolated databases, persistent volumes, shared and unique secrets: OK');
