import numpy as np

class TargetFilter:
    """Constant-velocity Kalman filter over normalized (x, y) in -1..1, time in seconds"""

    def __init__(self, accel_noise=1.5, measurement_noise=0.05, max_coast=0.6, reset_after=1.5):
        self.q = accel_noise **2
        self.r = measurement_noise **2
        self.max_coast = max_coast
        self.reset_after = reset_after
        self.x = None
        self.P = None
        self.t = 0.0

    def _predict(self, dt):
        """Predict the next state and covariance."""
        F = np.eye(4)
        F[0, 2] = F[1, 3] = dt
        d4, d3, d2 = dt ** 4 / 4, dt ** 3 / 2, dt ** 2
        Q = self.q * np.array([
            [d4, 0, d3, 0],
            [0, d4, 0, d3],
            [d3, 0, d2, 0],
            [0, d3, 0, d2]
        ])
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q

    def update(self, zx, zy, t):
        # A long gap likely means a different person, so start fresh.
        if self.x is None or t - self.t > self.reset_after:
            self.x = np.array([zx, zy, 0.0, 0.0])
            self.P = np.diag([self.r, self.r, 1.0, 1.0])
            self.t = t
            return
        self._predict(t - self.t)
        self.t = t
        H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]])
        S = H @ self.P @H.T + self.r * np.eye(2)
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ (np.array([zx, zy]) - H @ self.x)
        self.P = (np.eye(4) - K @ H) @ self.P

    def position(self, t):
        """Return the predicted position at time t, extrapolating briefly past the last update."""
        if self.x is None:
            return 0.0,0.0
        dt = min(max(t-self.t, 0.0), self.max_coast)
        x = np.clip(self.x[0] + self.x[2]*dt, -1.0, 1.0)
        y = np.clip(self.x[1] + self.x[3]*dt, -1.0, 1.0)
        return float(x), float(y)