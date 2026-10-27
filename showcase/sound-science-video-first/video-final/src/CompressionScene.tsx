import React from 'react';
import {Base,Field,Arrow,useTime,C} from './Common';
export const CompressionScene:React.FC=()=> <Base index={2}><Field time={useTime(2)} showBands/><Arrow x={420} y={835} width={1100} label="疏密变化与能量向前传播"/></Base>;
