// Local optimistic concurrency simulator. Integrate real receipts via existing owner adapter.
export function initialVersion(text='原始审核文稿'){return{base:{version:1,text},remote:{version:1,text},draft:text,status:'clean',proposal:null,history:[],allowed:true}}
export function versionReduce(state,e){const s=structuredClone(state);if(e.type==='edit'){if(typeof e.text!=='string'||e.text.length>200000)return{...s,status:'invalid-draft'};return{...s,draft:e.text,proposal:null,status:s.allowed?'dirty':'denied'}};if(e.type==='revoke')return{...s,allowed:false,remote:null,proposal:null,status:'denied'};if(!s.allowed)return{...s,status:'denied'};
 if(e.type==='remote')return Number.isSafeInteger(e.version)&&e.version>s.remote.version&&typeof e.text==='string'&&e.text.length<=200000?{...s,remote:{version:e.version,text:e.text}}:s;
 if(e.type==='save'){if(s.base.version!==s.remote.version)return{...s,status:'conflict'};s.history.push(s.remote);if(s.history.length>32)s.history.shift();s.remote={version:s.remote.version+1,text:s.draft};s.base=structuredClone(s.remote);s.status='saved-local';s.proposal=null;return s}
 if(e.type==='compare')return{...s,proposal:{against:s.remote.version,text:s.draft},status:'review'};
 if(e.type==='merge-edit'&&s.proposal&&typeof e.text==='string'&&e.text.length<=200000)return{...s,proposal:{...s.proposal,text:e.text}};
 if(e.type==='accept'&&s.proposal){if(s.proposal.against!==s.remote.version)return{...s,status:'conflict',proposal:null};s.history.push(s.remote);if(s.history.length>32)s.history.shift();s.remote={version:s.remote.version+1,text:s.proposal.text};s.base=structuredClone(s.remote);s.draft=s.remote.text;s.proposal=null;s.status='saved-local';s.proposal=null;return s}
 if(e.type==='cancel')return{...s,proposal:null,status:'dirty'};
 return s;
}
