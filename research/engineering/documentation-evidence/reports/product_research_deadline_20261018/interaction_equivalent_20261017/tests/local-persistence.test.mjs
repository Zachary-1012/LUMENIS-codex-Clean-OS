import test from 'node:test';import assert from 'node:assert/strict';
import{writeLocal,removeLocal}from'../src/local-persistence.mjs';
const memory=()=>{const data=new Map();return{getItem:k=>data.get(k)??null,setItem:(k,v)=>data.set(k,v),removeItem:k=>data.delete(k)}};
test('write is confirmed only after exact readback, including Unicode',()=>{const s=memory();assert.equal(writeLocal(s,'p',{text:'中文 한국어 العربية',version:1}).ok,true)});
test('silent ignored or transformed writes are not success',()=>{for(const getItem of [()=>null,()=>'{"truncated":true}'])assert.equal(writeLocal({setItem(){},getItem},'p',{x:1}).reason,'READBACK_MISMATCH')});
test('write and read errors preserve explicit failure',()=>{assert.equal(writeLocal({setItem(){throw Error()}},'p',{}).ok,false);assert.equal(writeLocal({setItem(){},getItem(){throw Error()}},'p',{}).ok,false)});
test('invalid serializable value is rejected',()=>{assert.equal(writeLocal(memory(),'p',undefined).reason,'INVALID_VALUE');const cyclic={};cyclic.self=cyclic;assert.equal(writeLocal(memory(),'p',cyclic).ok,false)});
test('reset removes only declared preferences and verifies absence',()=>{const s=memory();s.setItem('notes','keep');s.setItem('p','old');assert.equal(removeLocal(s,['p']).ok,true);assert.equal(s.getItem('notes'),'keep')});
test('partial reset reports every failed key and never claims all cleared',()=>{const s=memory();s.setItem('blocked','old');s.removeItem=k=>{if(k==='blocked')throw Error()};const r=removeLocal(s,['blocked','absent']);assert.equal(r.ok,false);assert.deepEqual(r.results,[{key:'blocked',ok:false},{key:'absent',ok:true}])});
