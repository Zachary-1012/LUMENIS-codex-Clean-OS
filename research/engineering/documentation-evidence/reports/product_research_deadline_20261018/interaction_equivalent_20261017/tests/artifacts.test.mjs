import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

test('study hashes never collide with persistent control IDs',()=>{
 const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
 for(const id of ['spring','magnet','inertia','flip','reveal','intelligent','aigc','optical','motion','trace','stream','revision','timeline','tasks','appearance'])assert.ok(!html.includes(`id="${id}"`));
});
