import React from 'react';
import {Base,Field,Arrow,useTime,C} from './Common';
export const ParallelScene:React.FC=()=> <Base index={3}><Field time={useTime(3)} opacity={.4} tagOnly/><Arrow x={700} y={470} width={420} double color={C.orange} label="空气的平均振动"/><Arrow x={440} y={760} width={1060} label="声波的传播方向"/><div style={{position:'absolute',left:1430,top:490,fontSize:90,color:C.paper,fontWeight:700}}>平行</div></Base>;
