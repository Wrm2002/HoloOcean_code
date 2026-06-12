"""Contains action space definitions"""

import numpy as np


class ActionSpace:
    """Abstract ActionSpace class.

    Parameters:
        shape (:obj:`list` of :obj:`int`): The shape of data that should be input to step or tick.
        buffer_shape (:obj:`list` of :obj:`int`, optional): The shape of the data that will be
            written to the shared memory.

            Only use this when it is different from shape.
    """

    def __init__(self, shape, buffer_shape=None):
        super(ActionSpace, self).__init__()
        self._shape = shape
        self.buffer_shape = buffer_shape or shape

    def sample(self):
        """Sample from the action space.

        Returns:
            (:obj:`np.ndarray`): A valid command to be input to step or tick.
        """
        raise NotImplementedError("Must be implemented by child class")

    @property
    def shape(self):
        """Get the shape of the action space.

        Returns:
            (:obj:`list` of :obj:`int`): The shape of the action space.
        """
        return self._shape

    def get_low(self):
        """The minimum value(s) for the action space.

        Returns:
            (:obj:`list` of :obj:`float` or :obj:`float`): the action space's minimum value(s)
        """
        raise NotImplementedError("Must be implemented by the child class")

    def get_high(self):
        """The maximum value(s) for the action space.

        Returns:
            (:obj:`list` of :obj:`float` or :obj:`float`): the action space's maximum value(s)
        """
        raise NotImplementedError("Must be implemented by the child class")


class ContinuousActionSpace(ActionSpace):
    """Action space that takes floating point inputs.

    Parameters:
        shape (:obj:`list` of :obj:`int`): The shape of data that should be input to step or tick.
        sample_fn (function, optional): A function that takes a shape parameter and outputs a
            sampled command.
        low (:obj:`list` of :obj:`float` or :obj:`float`): the low value(s) for the action space. Can be a scalar or an array
        high (:obj:`list` of :obj:`float` or :obj:`float`): the high value(s) for the action space. Cand be a scalar or an array

            If this is not given, it will default to sampling from a unit gaussian.
        buffer_shape (:obj:`list` of :obj:`int`, optional): The shape of the data that will be
            written to the shared memory.

            Only use this when it is different from ``shape``.
    """

    def __init__(self, shape, low=None, high=None, sample_fn=None, buffer_shape=None):
        super(ContinuousActionSpace, self).__init__(shape, buffer_shape=buffer_shape)
        self.sample_fn = sample_fn or ContinuousActionSpace._default_sample_fn
        self._low = low
        self._high = high

    def get_low(self):
        return self._low

    def get_high(self):
        return self._high

    def sample(self):
        return self.sample_fn(self._shape)

    def __repr__(self):
        return "[ContinuousActionSpace " + str(self._shape) + "]"

    @staticmethod
    def _default_sample_fn(shape):
        return np.random.normal(size=shape)


class DiscreteActionSpace(ActionSpace):
    """Action space that takes integer inputs.

    Args:
        shape (:obj:`list` of :obj:`int`): The shape of data that should be input to step or tick.
        low (:obj:`int`): The lowest value to sample.
        high (:obj:`int`): The highest value to sample.
        buffer_shape (:obj:`list` of :obj:`int`, optional): The shape of the data that will be
            written to the shared memory.

            Only use this when it is different from shape.
    """

    def __init__(self, shape, low, high, buffer_shape=None):
        super(DiscreteActionSpace, self).__init__(shape, buffer_shape=buffer_shape)
        self._low = low
        self._high = high

    def sample(self):
        return np.random.randint(self._low, self._high, self._shape, dtype=np.int32)

    def get_low(self):
        return self._low

    def get_high(self):
        return self._high

    def __repr__(self):
        return (
            "[DiscreteActionSpace "
            + str(self._shape)
            + ", min: "
            + str(self._low)
            + ", max: "
            + str(self._high)
            + "]"
        )


class SensorSpace:
    """Describes the observation space for a single sensor.

    This is a lightweight descriptor that captures the shape and data type
    of a sensor's output data, compatible with Gymnasium-style observation
    space definitions.

    Args:
        shape (tuple of int): The shape of the sensor data (e.g., (256, 256, 3))
        dtype (numpy dtype): The data type of the sensor output
        low (float or np.ndarray, optional): Lower bound of valid values
        high (float or np.ndarray, optional): Upper bound of valid values
    """

    def __init__(self, shape, dtype=np.float32, low=None, high=None):
        self.shape = tuple(shape) if hasattr(shape, '__iter__') else (shape,)
        self.dtype = np.dtype(dtype)
        self.low = low
        self.high = high

    @property
    def dtype_str(self):
        """Return the dtype as a string for serialization."""
        return str(self.dtype)

    def sample(self):
        """Sample a random observation from this sensor space.

        Returns:
            np.ndarray: Random data matching the sensor's shape and dtype.
        """
        if self.low is not None and self.high is not None:
            if np.issubdtype(self.dtype, np.integer):
                return np.random.randint(self.low, self.high + 1, self.shape).astype(self.dtype)
            return np.random.uniform(self.low, self.high, self.shape).astype(self.dtype)
        # Default: uniform random
        if np.issubdtype(self.dtype, np.integer):
            return np.random.randint(0, 256, self.shape).astype(self.dtype)
        return np.random.randn(*self.shape).astype(self.dtype)

    def __repr__(self):
        return f"SensorSpace(shape={self.shape}, dtype={self.dtype_str})"

    def __eq__(self, other):
        if not isinstance(other, SensorSpace):
            return False
        return self.shape == other.shape and self.dtype == other.dtype

    def to_gym_space(self):
        """Convert to a gymnasium Box space if gymnasium is available.

        Returns:
            gymnasium.spaces.Box or None: The equivalent Box space,
                or None if gymnasium is not installed.
        """
        try:
            import gymnasium as gym
            low = self.low
            high = self.high
            if low is not None and not isinstance(low, np.ndarray):
                low = np.full(self.shape, low, dtype=self.dtype)
            if high is not None and not isinstance(high, np.ndarray):
                high = np.full(self.shape, high, dtype=self.dtype)
            return gym.spaces.Box(
                low=-np.inf if low is None else low,
                high=np.inf if high is None else high,
                shape=self.shape,
                dtype=self.dtype,
            )
        except ImportError:
            return None
