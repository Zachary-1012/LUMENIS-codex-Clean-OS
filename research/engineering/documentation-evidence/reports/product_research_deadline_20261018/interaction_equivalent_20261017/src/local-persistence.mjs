/** Inject Storage at the view boundary. A successful write requires exact readback.
 * No retries, no server claims, and no deletion of unrelated user data. */
export function writeLocal(storage,key,value){
 try{const encoded=JSON.stringify(value);if(typeof encoded!=='string')return{ok:false,reason:'INVALID_VALUE'};storage.setItem(key,encoded);return storage.getItem(key)===encoded?{ok:true}:{ok:false,reason:'READBACK_MISMATCH'}}
 catch{return{ok:false,reason:'STORAGE_UNAVAILABLE'}}
}
export function removeLocal(storage,keys){
 const results=keys.map(key=>{try{storage.removeItem(key);return{key,ok:storage.getItem(key)===null}}catch{return{key,ok:false}}});
 return{ok:results.every(x=>x.ok),results};
}
