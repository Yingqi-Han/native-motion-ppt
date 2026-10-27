import {test} from 'node:test';
import assert from 'node:assert/strict';
import {cameraAt,displacement} from '../assets/science-video/src/physics.mjs';

test('tracking camera starts and ends at the original world coordinates',()=>{
 for(const [start,end] of [[7,15],[8,18]]){
  for(const t of [start-1,start,end,end+1]){const c=cameraAt(t,start,end);assert.equal(c.scale,1);assert.equal(c.focus,0);assert.ok(Math.abs(c.tx)<1e-9&&Math.abs(c.ty)<1e-9);}
  const c=cameraAt(start+2,start,end);
  assert.equal(c.scale,1.85);assert.equal(880*c.scale+c.tx,960);assert.equal(530*c.scale+c.ty,600);
 }
});
test('tagged parcel has no cut-induced position jump',()=>{
 for(const [start,end] of [[7,15],[8,18]])for(const cut of [start,end]){
  const point=t=>{const c=cameraAt(t,start,end);return [(880+displacement(880,t))*c.scale+c.tx,530*c.scale+c.ty];};
  const a=point(cut-1/30),b=point(cut);
  assert.ok(Math.hypot(a[0]-b[0],a[1]-b[1])<3);
 }
});
