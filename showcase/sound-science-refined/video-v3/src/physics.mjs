export const TAU = Math.PI * 2;
export const displacement = (x, time, a=24, wavelength=480, period=3, origin=340) => a*Math.sin(TAU*((x-origin)/wavelength-time/period));
export const compressionCenters = (time,wavelength=480,period=3,origin=340) => [-3,-2,-1,0,1,2,3,4].map(n=>origin+wavelength*((time/period)%1+.5+n)).filter(x=>x>180&&x<1790);

const smooth = (x) => {const t=Math.max(0,Math.min(1,x));return t*t*t*(t*(6*t-15)+10);};
// One world/camera across scene boundaries. At either cut the camera is identity.
export const cameraAt = (time,start,end) => {
 const focus=smooth((time-start)/1.1)*(1-smooth(time-(end-1)));
 const scale=1+.85*focus;
 return {scale,tx:focus*(960-880*1.85),ty:focus*(600-530*1.85),focus};
};
