"""Warm-start/cold-retry policy only; same transport market and precision."""
import time
import numpy as np
from batched_transport_newton_recovery_2025 import RecoveredTransportMarket


class RobustTransportMarket(RecoveredTransportMarket):
    def solve(self,theta,hours,p0=None,tolerance=1e-9,max_iterations=150):
        started=time.perf_counter()
        def timed(result):
            result['seconds']=time.perf_counter()-started
            return result
        # Neutral annual inference gets a reproducible model-only cold guess.
        # Fitting retains its own prior-iteration equilibrium warm start.
        if theta.ndim==2:p0=None
        try:return timed(super().solve(theta,hours,p0,tolerance,max_iterations))
        except RuntimeError:
            if p0 is not None:
                try:
                    result=super().solve(theta,hours,None,tolerance,max_iterations)
                    result['cold_retry']=True;return timed(result)
                except RuntimeError:pass
            offers=self.offers(theta,hours);guess=self.initial_prices(offers)
            # Safeguarded coordinate minimization is a numerical initializer,
            # never a replacement for the final full balance certificate.
            for sweep in range(3):
                guess=self.coordinate(guess,offers)
                try:
                    result=super().solve(theta,hours,guess,tolerance,max_iterations)
                    result['coordinate_initializer_sweeps']=sweep+1;return timed(result)
                except RuntimeError:pass
            raise RuntimeError('Cold/coordinate recovery failed; no capacity or residual gate was relaxed')
