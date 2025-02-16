from collections import deque
import time
import re


class TPSCalculator:
    """
    A class to calculate Transactions Per Second (TPS) based on block height changes over time.

    This class tracks the block height and calculates TPS over a configurable history size.
    It supports both fixed interval calculations and variable time-based calculations.

    :param history_size: Number of recent TPS values to keep for averaging.
    :type history_size: int
    :param sleep_time: Fixed interval between API calls in seconds.
    :type sleep_time: int
    :param variable_time: If True, calculate TPS based on actual elapsed time.
    :type variable_time: bool

    Example:
        .. code-block:: python

            # Initialize TPSCalculator with default parameters
            tps_calculator = TPSCalculator()

            # Simulate block height updates
            current_height = 100
            current_time = time.time()

            # Calculate TPS with a new block height
            current_tps, average_tps = tps_calculator.calculate_tps(current_height, current_time)

            print(f"Current TPS: {current_tps}, Average TPS: {average_tps}")

            # Reset the calculator if needed
            tps_calculator.reset()
    """

    def __init__(self, history_size=50, sleep_time=2, variable_time=False):
        """
        Initializes the TPSCalculator.

        :param history_size: Number of recent TPS values to keep for averaging.
        :type history_size: int
        :param sleep_time: Fixed interval between API calls in seconds.
        :type sleep_time: int
        :param variable_time: If True, calculate TPS based on actual elapsed time.
        :type variable_time: bool
        """
        self.previous_height = None
        self.previous_time = None
        self.tps_history = deque(maxlen=history_size)
        self.call_count = 0  # To track the number of API calls
        self.sleep_time = sleep_time
        self.variable_time = variable_time
        self.total_transactions = 0

    def calculate_tps(self, current_height, current_time=None):
        """
        Calculates the current TPS and updates the TPS history.

        :param current_height: The current block height.
        :type current_height: int
        :param current_time: The current timestamp. If None and variable_time is False, uses fixed sleep_time.
        :type current_time: float, optional
        :return: Tuple of (current_tps, average_tps)
        :rtype: tuple(float, float)
        """
        if not self.variable_time:
            time_diff = self.sleep_time
        else:
            if current_time is None:
                current_time = time.time()
            if self.previous_time is not None:
                time_diff = current_time - self.previous_time

                # Validate time_diff
                if time_diff <= 0:
                    print(f"Warning: Non-positive time_diff ({time_diff}). Skipping TPS calculation.")
                    return 0, self.get_average_tps()
                elif time_diff < 0.1:
                    print(f"Warning: Very small time_diff ({time_diff}). Adjusting to minimum threshold.")
                    time_diff = 0.1  # Set to minimum threshold to prevent inflated TPS
            else:
                time_diff = self.sleep_time

        if self.previous_height is not None:
            height_diff = current_height - self.previous_height

            # Validate height_diff
            if height_diff < 0:
                print(f"Warning: Negative height_diff ({height_diff}). Resetting TPS calculator.")
                self.reset()
                return 0, self.get_average_tps()

            if height_diff == 0:
                current_tps = 0
            else:
                current_tps = height_diff / time_diff
                max_tps = 1000  # Define a maximum reasonable TPS
                if current_tps > max_tps:
                    print(f"Warning: Unusually high TPS ({current_tps}). Capping to {max_tps}.")
                    current_tps = max_tps

                self.tps_history.append(current_tps)
                self.total_transactions += height_diff
        else:
            current_tps = 0

        self.previous_height = current_height
        if self.variable_time:
            self.previous_time = current_time

        average_tps = self.get_average_tps()
        self.call_count += 1

        return current_tps, average_tps

    def get_average_tps(self):
        """
        Calculates the average TPS from the history.

        :return: The average TPS.
        :rtype: float
        """
        return sum(self.tps_history) / len(self.tps_history) if self.tps_history else 0

    def processed_tx(self):
        """
        Returns the total number of transactions since monitoring started.

        :return: Total transactions as integer.
        :rtype: int
        """
        return self.total_transactions

    def last_n_tx(self):
        """
        Returns the number of transactions in the last n seconds (sleep_time).

        :return: Transactions count in last n seconds.
        :rtype: float
        """
        if self.tps_history:
            return self.tps_history[-1] * self.sleep_time
        else:
            return 0

    def reset(self):
        """
        Resets the TPSCalculator to its initial state.

        This clears all stored data and resets counters.

        :return: None
        """
        self.previous_height = None
        self.previous_time = None
        self.tps_history.clear()
        self.call_count = 0


class SyncSpeedTracker:
    """
    A class to track the synchronization speed of a blockchain node.

    This class calculates the average number of blocks synchronized per second
    using a moving average approach based on recent block height and time differences.

    :param history_size: The number of records to keep for calculating the moving average.
    :type history_size: int

    Example:
        .. code-block:: python

            # Initialize the tracker with a history size of 10
            sync_tracker = SyncSpeedTracker(history_size=10)

            # Update the tracker with new block height and timestamp
            current_height = 150
            current_time = time.time()
            sync_tracker.update(current_height, current_time)

            # Get the average synchronization speed (blocks per second)
            avg_sync_speed = sync_tracker.get_average_sync_speed()
            print(f"Average Sync Speed: {avg_sync_speed} blocks/second")
    """

    def __init__(self, history_size=10):
        """
        Initializes the SyncSpeedTracker.

        :param history_size: The number of records to store for calculating the moving average.
        :type history_size: int
        """
        self.history_size = history_size
        self.block_differences = deque(maxlen=history_size)
        self.time_differences = deque(maxlen=history_size)
        self.previous_height = None
        self.previous_time = None

    def update(self, current_height, current_time):
        """
        Updates the synchronization speed tracker with new block height and timestamp.

        :param current_height: The current block height.
        :type current_height: int
        :param current_time: The current timestamp.
        :type current_time: float
        """
        if self.previous_height is not None and self.previous_time is not None:
            block_diff = current_height - self.previous_height
            time_diff = current_time - self.previous_time

            if block_diff > 0 and time_diff > 0:
                self.block_differences.append(block_diff)
                self.time_differences.append(time_diff)

        self.previous_height = current_height
        self.previous_time = current_time

    def get_average_sync_speed(self):
        """
        Calculates the average number of blocks synchronized per second using a moving average.

        :return: The average synchronization speed in blocks per second. Returns None if insufficient data.
        :rtype: float or None
        """
        if not self.block_differences or not self.time_differences:
            return None  # Insufficient data

        total_blocks = sum(self.block_differences)
        total_time = sum(self.time_differences)

        if total_time > 0:
            return total_blocks / total_time  # Blocks per second
        else:
            return None


class BlockDifferenceTracker:
    """
    A class to track and calculate the average block difference over a configurable history size.

    This class is useful for monitoring the difference in block heights between nodes or systems.

    :param history_size: The number of recent block differences to track.
    :type history_size: int

    Example:
        .. code-block:: python

            # Initialize the tracker with a history size of 50
            block_tracker = BlockDifferenceTracker(history_size=50)

            # Add block differences
            block_tracker.add_difference(5)
            block_tracker.add_difference(3)

            # Get the average block difference
            avg_difference = block_tracker.get_average_difference()
            print(f"Average Block Difference: {avg_difference}")
    """

    def __init__(self, history_size=100):
        """
        Initializes the BlockDifferenceTracker.

        :param history_size: Number of recent block differences to track.
        :type history_size: int
        """
        self.differences = deque(maxlen=history_size)

    def add_difference(self, block_difference):
        """
        Adds a new block difference to the tracker.

        :param block_difference: The current block difference.
        :type block_difference: int
        """
        self.differences.append(block_difference)

    def get_average_difference(self):
        """
        Calculates the average block difference.

        :return: The average of the tracked block differences.
        :rtype: float
        """
        if not self.differences:
            return 0
        return sum(self.differences) / len(self.differences)


class LatencyTracker:
    """
    A class to track and analyze latency measurements.

    This class stores latency values and provides methods to calculate average, minimum, and maximum latencies.

    :param history_size: The number of recent latency measurements to track.
    :type history_size: int

    Example:
        .. code-block:: python

            # Initialize the tracker with a history size of 100
            latency_tracker = LatencyTracker(history_size=100)

            # Add latency measurements
            latency_tracker.add_latency(120)
            latency_tracker.add_latency(150)

            # Get latency statistics
            avg_latency = latency_tracker.get_average_latency()
            min_latency = latency_tracker.get_min_latency()
            max_latency = latency_tracker.get_max_latency()

            print(f"Average Latency: {avg_latency} ms")
            print(f"Min Latency: {min_latency} ms")
            print(f"Max Latency: {max_latency} ms")
    """

    def __init__(self, history_size=100):
        """
        Initializes the LatencyTracker.

        :param history_size: The number of recent latency measurements to track.
        :type history_size: int
        """
        self.latencies = deque(maxlen=history_size)

    def add_latency(self, latency):
        """
        Adds a new latency measurement to the tracker.

        :param latency: The measured latency in milliseconds.
        :type latency: float
        """
        self.latencies.append(latency)

    def get_average_latency(self):
        """
        Calculates the average latency from the tracked measurements.

        :return: The average latency in milliseconds.
        :rtype: float
        """
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0

    def get_min_latency(self):
        """
        Returns the minimum recorded latency.

        :return: The minimum latency in milliseconds, or None if no data is available.
        :rtype: float or None
        """
        return min(self.latencies) if self.latencies else None

    def get_max_latency(self):
        """
        Returns the maximum recorded latency.

        :return: The maximum latency in milliseconds, or None if no data is available.
        :rtype: float or None
        """
        return max(self.latencies) if self.latencies else None


class ErrorRateTracker:
    """
    A class to track and calculate error rates for API requests or operations.

    This class monitors total requests and failed requests to compute an error rate percentage.

    Example:
        .. code-block:: python

            # Initialize the tracker
            error_tracker = ErrorRateTracker()

            # Record requests (success=True for successful requests)
            error_tracker.record_request(success=True)
            error_tracker.record_request(success=False)

            # Get the current error rate
            error_rate = error_tracker.get_error_rate()
            print(f"Error Rate: {error_rate:.2f}%")
    """

    def __init__(self):
        """
        Initializes the ErrorRateTracker.

        Tracks total and failed requests for calculating error rates.
        """
        self.total_requests = 0
        self.failed_requests = 0

    def record_request(self, success=True):
        """
        Records a request and whether it was successful or not.

        :param success: True if the request was successful; False otherwise.
                        Defaults to True.
        :type success: bool
        """
        self.total_requests += 1
        if not success:
            self.failed_requests += 1

    def get_error_rate(self):
        """
        Calculates the error rate as a percentage of failed requests over total requests.

        :return: The error rate percentage. Returns 0 if no requests have been recorded.
        :rtype: float
        """
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100


class ThroughputTracker:
    """
    A class to track and calculate throughput (requests per second).

    This class records timestamps of requests and calculates the throughput
    over a configurable history size.

    :param history_size: The number of recent timestamps to track.
    :type history_size: int

    Example:
        .. code-block:: python

            # Initialize the tracker with a history size of 100
            throughput_tracker = ThroughputTracker(history_size=100)

            # Record requests with timestamps
            throughput_tracker.record_request()
            time.sleep(1)
            throughput_tracker.record_request()

            # Get the current throughput
            throughput = throughput_tracker.get_throughput()
            print(f"Throughput: {throughput} requests/second")
    """

    def __init__(self, history_size=100):
        """
        Initializes the ThroughputTracker.

        :param history_size: The number of recent timestamps to track.
        :type history_size: int
        """
        self.timestamps = deque(maxlen=history_size)

    def record_request(self, timestamp=None):
        """
        Records the timestamp of a request.

        :param timestamp: The timestamp of the request. Defaults to the current time.
        :type timestamp: float, optional
        """
        self.timestamps.append(timestamp or time.time())

    def get_throughput(self):
        """
        Calculates the throughput (requests per second).

        :return: The calculated throughput. Returns 0 if insufficient data.
        :rtype: float
        """
        if len(self.timestamps) < 2:
            return 0
        duration = self.timestamps[-1] - self.timestamps[0]
        return len(self.timestamps) / duration if duration > 0 else 0


class PeriodicMetricLogger:
    """
    A class for logging metrics at regular intervals.

    This class logs provided metrics only if a specified interval has passed since the last log.

    :param interval: The logging interval in seconds.
    :type interval: int

    Example:
        .. code-block:: python

            # Initialize the logger with a 10-second interval
            metric_logger = PeriodicMetricLogger(interval=10)

            # Log metrics periodically
            metrics = {"TPS": 50.5, "Latency": 120}
            metric_logger.log_metrics(metrics)
    """

    def __init__(self, interval=10):
        """
        Initializes the PeriodicMetricLogger.

        :param interval: The logging interval in seconds.
        :type interval: int
        """
        self.interval = interval
        self.last_logged = time.time()

    def log_metrics(self, metrics):
        """
        Logs the provided metrics if the logging interval has passed.

        :param metrics: A dictionary of metric names and their values.
        :type metrics: dict
        """
        current_time = time.time()
        if current_time - self.last_logged >= self.interval:
            for key, value in metrics.items():
                print(f"{key}: {value}")
            self.last_logged = current_time


class SpikeDetector:
    """
    A class to detect spikes in a series of values.

    A spike is detected when the difference between consecutive values exceeds a specified threshold.

    :param threshold: The change amount considered as a spike.
    :type threshold: float
    :param history_size: The maximum number of recent values to store.
    :type history_size: int

    Example:
        .. code-block:: python

            # Initialize the spike detector with a threshold of 10
            spike_detector = SpikeDetector(threshold=10, history_size=5)

            # Add values and detect spikes
            spike_detector.add_value(50)
            spike_detector.add_value(65)

            is_spike = spike_detector.detect_spike()
            print(f"Spike Detected: {is_spike}")
    """

    def __init__(self, threshold, history_size=10):
        """
        Initializes the SpikeDetector.

        :param threshold: The change amount considered as a spike.
        :type threshold: float
        :param history_size: The maximum number of recent values to store.
        :type history_size: int
        """
        self.threshold = threshold
        self.values = deque(maxlen=history_size)

    def add_value(self, value):
        """
        Adds a new value to the tracker.

        :param value: The new value to track.
        :type value: float
        """
        self.values.append(value)

    def detect_spike(self):
        """
        Detects whether a spike occurred based on recent values.

        :return: True if a spike is detected; False otherwise.
        :rtype: bool
        """
        if len(self.values) < 2:
            return False
        last_value = self.values[-1]
        prev_value = self.values[-2]
        return abs(last_value - prev_value) > self.threshold


class AnomalyDetector:
    """
    A class to detect anomalies in data based on a baseline and tolerance.

    An anomaly is detected when a value deviates from the baseline by more than the allowed tolerance.

    :param baseline: The reference value for normal data (e.g., average TPS).
    :type baseline: float
    :param tolerance: The acceptable deviation from the baseline as a fraction (e.g., 0.2 for ±20%).
                      Defaults to 0.2 (±20%).
    :type tolerance: float

    Example:
        .. code-block:: python

            # Initialize the anomaly detector with a baseline of 50 and tolerance of 20%
            anomaly_detector = AnomalyDetector(baseline=50, tolerance=0.2)

            # Detect anomalies in new values
            is_anomaly = anomaly_detector.detect_anomaly(65)
            print(f"Anomaly Detected: {is_anomaly}")
    """

    def __init__(self, baseline, tolerance=0.2):
        """
        Initializes the AnomalyDetector.

        :param baseline: The reference value for normal data (e.g., average TPS).
        :type baseline: float
        :param tolerance: The acceptable deviation from the baseline as a fraction.
                          Defaults to 0.2 (±20%).
        :type tolerance: float
        """
        self.baseline = baseline
        self.tolerance = tolerance

    def detect_anomaly(self, value):
        """
        Detects whether a given value is an anomaly based on the baseline and tolerance.

        :param value: The value to check for anomalies.
        :type value: float
        :return: True if the value is an anomaly; False otherwise.
        :rtype: bool

        Example:
            .. code-block:: python

                # Check if a value is an anomaly
                is_anomaly = anomaly_detector.detect_anomaly(75)
                print(f"Anomaly Detected: {is_anomaly}")
        """
        lower_bound = self.baseline * (1 - self.tolerance)
        upper_bound = self.baseline * (1 + self.tolerance)
        return not (lower_bound <= value <= upper_bound)


class TrendAnalyzer:
    """
    A class to analyze trends in a series of values.

    This class tracks a series of values and determines whether the trend is upward, downward, or stable.

    :param history_size: The maximum number of recent values to store for trend analysis.
    :type history_size: int

    Example:
        .. code-block:: python

            # Initialize the trend analyzer with a history size of 5
            trend_analyzer = TrendAnalyzer(history_size=5)

            # Add values to the trend analyzer
            trend_analyzer.add_value(10)
            trend_analyzer.add_value(15)
            trend_analyzer.add_value(20)

            # Get the current trend
            trend = trend_analyzer.get_trend()
            print(f"Current Trend: {trend}")
    """

    def __init__(self, history_size=10):
        """
        Initializes the TrendAnalyzer.

        :param history_size: The maximum number of recent values to store for trend analysis.
        :type history_size: int
        """
        self.values = deque(maxlen=history_size)

    def add_value(self, value):
        """
        Adds a new value to the tracker.

        :param value: The new value to track.
        :type value: float or int
        """
        self.values.append(value)

    def get_trend(self):
        """
        Calculates the trend based on the stored values.

        The trend is determined as:
        - "upward": If all differences between consecutive values are positive.
        - "downward": If all differences between consecutive values are negative.
        - "stable": If there is no consistent upward or downward pattern.

        :return: The calculated trend ("upward", "downward", or "stable").
        :rtype: str

        Example:
            .. code-block:: python

                # Analyze the trend
                trend = trend_analyzer.get_trend()
                print(f"Current Trend: {trend}")
        """
        if len(self.values) < 2:
            return "stable"

        diffs = [self.values[i + 1] - self.values[i] for i in range(len(self.values) - 1)]

        if all(d > 0 for d in diffs):
            return "upward"
        elif all(d < 0 for d in diffs):
            return "downward"

        return "stable"


class RollingAverageCalculator:
    """
    A class to calculate the rolling (moving) average of a series of values.

    This class maintains a fixed-size window of recent values and calculates the average
    of the values within the window.

    :param window_size: The size of the rolling window.
    :type window_size: int

    Example:
        .. code-block:: python

            # Initialize the rolling average calculator with a window size of 5
            avg_calculator = RollingAverageCalculator(window_size=5)

            # Add values to the calculator
            avg_calculator.add_value(10)
            avg_calculator.add_value(20)
            avg_calculator.add_value(30)

            # Get the current rolling average
            average = avg_calculator.get_average()
            print(f"Rolling Average: {average}")
    """

    def __init__(self, window_size=5):
        """
        Initializes the RollingAverageCalculator.

        :param window_size: The size of the rolling window.
        :type window_size: int
        """
        self.window_size = window_size
        self.values = deque(maxlen=window_size)

    def add_value(self, value):
        """
        Adds a new value to the rolling window.

        :param value: The new value to add.
        :type value: float or int
        """
        self.values.append(value)

    def get_average(self):
        """
        Calculates and returns the rolling average of the stored values.

        :return: The rolling average. Returns 0 if no values are stored.
        :rtype: float

        Example:
            .. code-block:: python

                # Calculate the rolling average
                average = avg_calculator.get_average()
                print(f"Rolling Average: {average}")
        """
        return sum(self.values) / len(self.values) if self.values else 0


class ThresholdNotifier:
    """
    A class to monitor values and trigger a notification when a threshold is exceeded.

    This class checks if a given value exceeds a predefined threshold and executes
    a callback function when the threshold is crossed.

    :param threshold: The threshold value to monitor.
    :type threshold: float or int
    :param alert_callback: A callback function to execute when the threshold is exceeded.
    :type alert_callback: callable

    Example:
        .. code-block:: python

            # Define an alert callback function
            def alert(value):
                print(f"Alert! Value exceeded: {value}")

            # Initialize the notifier with a threshold of 100
            notifier = ThresholdNotifier(threshold=100, alert_callback=alert)

            # Check values and trigger alerts if necessary
            notifier.check_and_notify(120)  # This will trigger the alert
            notifier.check_and_notify(80)   # This will not trigger the alert
    """

    def __init__(self, threshold, alert_callback):
        """
        Initializes the ThresholdNotifier.

        :param threshold: The threshold value to monitor.
        :type threshold: float or int
        :param alert_callback: A callback function to execute when the threshold is exceeded.
        :type alert_callback: callable
        """
        self.threshold = threshold
        self.alert_callback = alert_callback

    def check_and_notify(self, value):
        """
        Checks if the given value exceeds the threshold and triggers the callback if it does.

        :param value: The value to check against the threshold.
        :type value: float or int

        Example:
            .. code-block:: python

                notifier.check_and_notify(150)  # Triggers the callback if value > threshold
        """
        if value > self.threshold:
            self.alert_callback(value)


class RateLimiter:
    """
    A class to enforce rate limits on operations.

    This class ensures that a maximum number of calls can be made within a specified time period.
    If the limit is exceeded, further calls are not allowed until the time window resets.

    :param max_calls: The maximum number of calls allowed within the time period.
    :type max_calls: int
    :param time_period: The time period (in seconds) for rate limiting.
    :type time_period: float or int

    Example:
        .. code-block:: python

            # Initialize a rate limiter allowing 5 calls per 10 seconds
            rate_limiter = RateLimiter(max_calls=5, time_period=10)

            # Check if calls are allowed
            for i in range(10):
                if rate_limiter.is_allowed():
                    print(f"Call {i + 1}: Allowed")
                else:
                    print(f"Call {i + 1}: Rate limit exceeded")
                time.sleep(1)  # Simulate time delay between calls
    """

    def __init__(self, max_calls, time_period):
        """
        Initializes the RateLimiter.

        :param max_calls: The maximum number of calls allowed within the time period.
        :type max_calls: int
        :param time_period: The time period (in seconds) for rate limiting.
        :type time_period: float or int
        """
        self.max_calls = max_calls
        self.time_period = time_period
        self.calls = deque()

    def is_allowed(self):
        """
        Checks if a new call is allowed under the rate limit.

        Removes expired calls from the queue based on the current time and time period,
        then determines if another call can be made.

        :return: True if the call is allowed; False otherwise.
        :rtype: bool

        Example:
            .. code-block:: python

                if rate_limiter.is_allowed():
                    print("Call allowed")
                else:
                    print("Rate limit exceeded")
        """
        current_time = time.time()

        # Remove timestamps outside of the current time window
        while self.calls and self.calls[0] < current_time - self.time_period:
            self.calls.popleft()

        # Check if we can allow another call
        if len(self.calls) < self.max_calls:
            self.calls.append(current_time)
            return True

        return False


def calculate_reset_percentage(data):
    match = re.search(r'height=(\d+) resolved=(\d+) unresolved=(\d+)', data)

    if match:
        height = int(match.group(1))         # height
        resolved = int(match.group(2))       # resolved
        unresolved = int(match.group(3))     # unresolved
        reset_percentage = (resolved / height) * 100

        return {
            "height": height,
            "resolved": resolved,
            "unresolved": unresolved,
            "progress": round(reset_percentage, 2)
        }
    else:
        raise ValueError("Cant parsing data")


def calculate_pruning_percentage(data):
    match = re.search(r'pruning (\d+)/(\d+)\s+resolved=(\d+) unresolved=(\d+)', data)

    if match:
        current = int(match.group(1))
        total = int(match.group(2))
        resolved = int(match.group(3))
        unresolved = int(match.group(4))

        progress_percentage = (current / total) * 100
        resolve_progress_percentage = (resolved / total) * 100
        # progress_percentage = (resolved / (resolved + unresolved)) * 100
        # 전체 처리해야 할 항목 수 추정
        # estimated_total = resolved + unresolved

        # 진행률 계산
        # progress_percentage = (resolved / estimated_total) * 100

        return {
            "current": current,
            "total": total,
            "resolved": resolved,
            "unresolved": unresolved,
            "resolve_progress_percentage": round(resolve_progress_percentage, 2),
            "progress": round(progress_percentage, 2),
        }
    else:
        raise ValueError("Cant parsing data")
