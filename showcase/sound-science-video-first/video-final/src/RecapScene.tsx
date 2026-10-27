import React from 'react';
import {Base,Field,Arrow,C,useTime} from './Common';
export const RecapScene:React.FC=()=> <Base index={6} title="记住这两个方向。"><Field time={useTime(6)}/><Arrow x={750} y={355} width={260} double color={C.orange} label="空气局部往复"/><Arrow x={450} y={840} width={1050} label="声波向外传播"/></Base>;
