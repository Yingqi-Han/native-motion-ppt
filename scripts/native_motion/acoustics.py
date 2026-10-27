"""Small, explicit linear-acoustics illustration model; no simulation claims."""
import math


def wavelength(speed=343.0, frequency=440.0):
    if not all(math.isfinite(x) and x > 0 for x in (speed, frequency)):
        raise ValueError('speed and frequency must be finite and positive')
    return speed/frequency


def displacement(x, time, amplitude=24.0, wavelength_px=480.0, period=3.0, origin=340.0):
    return amplitude*math.sin(2*math.pi*((x-origin)/wavelength_px-time/period))


def pressure_proxy(x, time, wavelength_px=480.0, period=3.0, origin=340.0):
    """-du/dx up to a positive constant, not an absolute pressure in pascals."""
    return -math.cos(2*math.pi*((x-origin)/wavelength_px-time/period))


def parcels(time, model):
    a, lam, period = model['amplitude_px'], model['wavelength_px'], model['period_seconds']
    if min(lam, period, model['parcel_spacing_px']) <= 0 or not 0 <= a*2*math.pi/lam < 1:
        raise ValueError('Illustration must have positive scales and non-crossing parcels')
    return [dict(id=f'parcel-{row}-{col}', column=col, row=row,
                 x0=model['origin_x']+col*model['parcel_spacing_px'],
                 x=model['origin_x']+col*model['parcel_spacing_px']+
                   displacement(model['origin_x']+col*model['parcel_spacing_px'],time,a,lam,period,model['origin_x']),
                 y=model['origin_y']+row*model['row_spacing_px'],
                 tagged=(col==model['tagged_column'] and row==model['tagged_row']))
            for row in range(model['rows']) for col in range(model['columns'])]
