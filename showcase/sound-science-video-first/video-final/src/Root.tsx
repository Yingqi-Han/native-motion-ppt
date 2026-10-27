import React from 'react';
import {Composition,Folder,Series,useVideoConfig} from 'remotion';
import {QuestionScene} from './QuestionScene';
import {ParcelScene} from './ParcelScene';
import {CompressionScene} from './CompressionScene';
import {ParallelScene} from './ParallelScene';
import {FrequencyScene} from './FrequencyScene';
import {WavelengthScene} from './WavelengthScene';
import {RecapScene} from './RecapScene';
import {CreditsScene} from './CreditsScene';
export const SoundJourney:React.FC=()=>{const {fps}=useVideoConfig();return <Series><Series.Sequence name="question" durationInFrames={8*fps} premountFor={fps}><QuestionScene/></Series.Sequence>
<Series.Sequence name="parcel" durationInFrames={10*fps} premountFor={fps}><ParcelScene/></Series.Sequence>
<Series.Sequence name="compression" durationInFrames={10*fps} premountFor={fps}><CompressionScene/></Series.Sequence>
<Series.Sequence name="parallel" durationInFrames={8*fps} premountFor={fps}><ParallelScene/></Series.Sequence>
<Series.Sequence name="frequency" durationInFrames={12*fps} premountFor={fps}><FrequencyScene/></Series.Sequence>
<Series.Sequence name="wavelength" durationInFrames={14*fps} premountFor={fps}><WavelengthScene/></Series.Sequence>
<Series.Sequence name="recap" durationInFrames={8*fps} premountFor={fps}><RecapScene/></Series.Sequence>
<Series.Sequence name="credits" durationInFrames={4*fps} premountFor={fps}><CreditsScene/></Series.Sequence></Series>};
export const Root:React.FC=()=> <><Composition id="SoundJourney" component={SoundJourney} width={1920} height={1080} fps={30} durationInFrames={2220}/><Folder name="Scenes"><Composition id="Question" component={QuestionScene} width={1920} height={1080} fps={30} durationInFrames={240}/>
<Composition id="Parcel" component={ParcelScene} width={1920} height={1080} fps={30} durationInFrames={300}/>
<Composition id="Compression" component={CompressionScene} width={1920} height={1080} fps={30} durationInFrames={300}/>
<Composition id="Parallel" component={ParallelScene} width={1920} height={1080} fps={30} durationInFrames={240}/>
<Composition id="Frequency" component={FrequencyScene} width={1920} height={1080} fps={30} durationInFrames={360}/>
<Composition id="Wavelength" component={WavelengthScene} width={1920} height={1080} fps={30} durationInFrames={420}/>
<Composition id="Recap" component={RecapScene} width={1920} height={1080} fps={30} durationInFrames={240}/>
<Composition id="Credits" component={CreditsScene} width={1920} height={1080} fps={30} durationInFrames={120}/></Folder></>;
