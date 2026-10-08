import {pathToFileURL, fileURLToPath} from 'node:url';
import path from 'node:path';
import {promisify} from 'node:util';
import {execFile} from 'node:child_process';
const sdk = process.env.LUMENIS_MCP_SDK;
if (!sdk) throw new Error('LUMENIS_MCP_SDK must point to the reviewed local SDK');
const load = (p) => import(pathToFileURL(path.join(sdk, 'dist/esm', p)).href);
const {Server} = await load('server/index.js');
const {StdioServerTransport} = await load('server/stdio.js');
const {ListToolsRequestSchema, CallToolRequestSchema} = await load('types.js');
const execute = promisify(execFile);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const python = process.env.LUMENIS_PYTHON || 'python';
const empty = {type: 'object', properties: {}, additionalProperties: false};
const definitions = [
  ['source_read', 'Read bounded repository source using the in-repo reviewed source-navigation helper. No secrets or data paths.', {type:'object',properties:{path:{type:'string'},start:{type:'integer',minimum:1},limit:{type:'integer',minimum:1,maximum:250}},required:['path'],additionalProperties:false},true],
  ['route_task', 'Map an engineering task to existing skills and tools. Does not grant permissions or execute tasks.', {type:'object',properties:{task:{type:'string',maxLength:6000},paths:{type:'array',maxItems:100,items:{type:'string'}}},required:['task'],additionalProperties:false},true],
  ['static_check', 'Parse Python source without importing it; report source hashes. Not a test or E2E pass.', {type:'object',properties:{paths:{type:'array',maxItems:100,items:{type:'string'}}},required:['paths'],additionalProperties:false},true],
  ['validation_plan', 'Read current source fingerprints and suggest proportional validation tiers; no execution.', {type:'object',properties:{paths:{type:'array',maxItems:100,items:{type:'string'}}},required:['paths'],additionalProperties:false},true],
  ['capabilities', 'Non-secret current capability configuration inventory. Configured is not live-verified.', empty, true],

  ['repo_truth', 'Read local HEAD, cached origin/main and dirty count without changing the repository.', empty, true],
  ['runtime_health', 'Read the loopback core health endpoint; not an E2E acceptance result.', empty, true],
  ['config_inventory', 'Read non-secret Codex/MCP/skill inventory; configured does not mean verified.', empty, true],
  ['source_owner', 'Find bounded excerpts in the current local LUMENIS source owner index.', {type:'object', properties:{query:{type:'string', maxLength:80}}, required:['query'], additionalProperties:false}, true],
  ['verification_plan', 'Plan retained static, build, security/data and real-user verification; no unit/integration suites or execution.', {type:'object', properties:{paths:{type:'array', maxItems:100, items:{type:'string'}}}, required:['paths'], additionalProperties:false}, true],
];
const server = new Server({name:'lumenis-engineering', version:'1.0.0'}, {capabilities:{tools:{}}});
server.setRequestHandler(ListToolsRequestSchema, async () => ({tools:definitions.map(([name,description,inputSchema,readOnlyHint]) => ({name,description,inputSchema,annotations:{readOnlyHint,destructiveHint:false,openWorldHint:false}}))}));
server.setRequestHandler(CallToolRequestSchema, async ({params}) => {
  const definition = definitions.find(x=>x[0]===params.name);
  if (!definition) throw new Error('Unknown tool');
  const args = params.arguments || {};
  const allowed = Object.keys(definition[2].properties);
  if (Object.keys(args).some(x=>!allowed.includes(x))) throw new Error('Unexpected argument');
  try {
    const {stdout} = await execute(python, ['-X','utf8',path.join(root,'.codex','engineering.py'),params.name,'--params',JSON.stringify(args)], {cwd:root,timeout:95000,maxBuffer:1000000,windowsHide:true});
    const result = JSON.parse(stdout);
    return {content:[{type:'text',text:JSON.stringify(result)}],structuredContent:result,isError:result.exit_code != null && result.exit_code !== 0};
  } catch (error) {
    return {content:[{type:'text',text:JSON.stringify({status:'ERROR',code:error.code ?? 'execution-failed'})}],isError:true};
  }
});
await server.connect(new StdioServerTransport());
