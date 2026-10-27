export const TAU = Math.PI * 2;
export const displacement = (x: number, time: number, a=24, wavelength=480, period=3, origin=340) => a*Math.sin(TAU*((x-origin)/wavelength-time/period));
export const compressionCenters = (time:number,wavelength=480,period=3,origin=340) => [-3,-2,-1,0,1,2,3,4].map(n=>origin+wavelength*((time/period)%1+.5+n)).filter(x=>x>180&&x<1790);
