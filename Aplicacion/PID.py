import math
import time

class G2_PID:
    def __init__(self, setPoint=0.0, Kp=0.2, Ki=0.0, Kd=0.0, fc=0, Kw=0.3, Vmax=1.0, awu="sat"):
        self.lastTime = time.time()
        self.setPoint = setPoint
        self.set_PID_param(Kp, Ki, Kd, fc, Kw)
        self.Vmax = Vmax   # 1.0 es es valor que se limita en archivo QuadrupleTanks
        self.prev_yf = 0.0
        self.integral = 0.0
        self.u = 0.0
        self.awu = awu  # define el tipo de anti wind-up

    def update(self, input):

        # Time calc
        currentTime = time.time()
        Ts = currentTime - self.lastTime  # Calcula Ts como la diferencia entre el tiempo actual y el último cálculo
        self.lastTime = currentTime  # Actualiza el último tiempo registrado

        # Instant and integral error
        error = self.setPoint - input
        newIntegral = self.integral + Ts*error # añadimos el error actual al acumulado

        # Filter on measurement (Exponential Moving Average) + derivative on measurement
        EMA_alpha = self.calc_EMA_alpha(Ts)
        yf = EMA_alpha * input + (1 - EMA_alpha) * self.prev_yf
        yd = (yf - self.prev_yf) / Ts
        self.prev_yf = yf

        # Control
        output = self.Kp * error + self.Ki * newIntegral + self.Kd * yd

        # Saturación de la salida
        if output > self.Vmax:
            outputLimited = self.Vmax # el programa viene con umax = 10
        elif output < 0.0:
            outputLimited = 0.0
        else:
            outputLimited = output
        self.u = outputLimited

        # Anti wind-up for integral
        if self.awu == "back":
            self.integral += Ts * self.Kw * (outputLimited - output) # Anti wind-up with back-calculation
        elif self.awu == "sat" and outputLimited < output:
            self.integral = newIntegral # Simple saturation anti-windup (optional)

        return self.u if self.u >= 0.0 else 0.0

    def set_setPoint(self, setPoint):
        self.setPoint = setPoint
        self.integral = 0   # se resetea el error integral

    def set_PID_param(self, Kp, Ki, Kd, fc, Kw):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.fc = fc
        self.Kw = Kw

    def calc_EMA_alpha(self, Ts):
        fn = self.fc * Ts  # frecuencia normalizada por tasa de muestreo
        if fn <= 0:
            return 1
        else: 
            # α(fₙ) = cos(2πfₙ) - 1 + √( cos(2πfₙ)² - 4 cos(2πfₙ) + 3 )
            c = math.cos(2 * math.pi * fn)
            return c - 1 + math.sqrt(c**2 - 4*c + 3) 

