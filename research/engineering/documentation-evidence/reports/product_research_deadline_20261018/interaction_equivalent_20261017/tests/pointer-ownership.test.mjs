import test from 'node:test';import assert from 'node:assert/strict';import{beginDrag,moveDrag,endDrag}from'../src/direct-input.mjs';

test('a second pointer cannot finish another pointer drag',()=>{
 const s=beginDrag({pointerId:7,clientX:10,clientY:10,timeMs:0,objectX:0,objectY:0});
 const moved=moveDrag(s,{pointerId:7,clientX:30,clientY:10,timeMs:20}).state;
 assert.deepEqual(endDrag(moved,25,8),moved);
 assert.equal(endDrag(moved,25,7).active,false);
});
