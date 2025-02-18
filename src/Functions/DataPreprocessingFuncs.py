import pandas as pd
from pennylane import numpy as np
from matplotlib import pyplot as plt
from tqdm import tqdm
from typing import Literal
import os


def load_data(dataset, usecols=all, skiprows=None, sample_size=all, bool_plot=False):
    """
    Loads a specified subset of a csv file. Documentation source: https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html

            Parameters:
                    dataset (str, path object or file-like object): Any valid string path is acceptable. The string could be a URL. Valid URL schemes include http, ftp, s3, gs, and file. For file URLs, a host is expected. A local file could be: file://localhost/path/to/table.csv. If you want to pass in a path object, pandas accepts any os.PathLike. By file-like object, we refer to objects with a read() method, such as a file handle (e.g. via builtin open function) or StringIO.
                    usecols (list-like or callable, optional): Return a subset of the columns. If list-like, all elements must either be positional (i.e. integer indices into the document columns) or strings that correspond to column names provided either by the user in names or inferred from the document header row(s). If names are given, the document header row(s) are not taken into account. For example, a valid list-like usecols parameter would be [0, 1, 2] or ['foo', 'bar', 'baz']. Element order is ignored, so usecols=[0, 1] is the same as [1, 0]. To instantiate a DataFrame from data with element order preserved use pd.read_csv(data, usecols=['foo', 'bar'])[['foo', 'bar']] for columns in ['foo', 'bar'] order or pd.read_csv(data, usecols=['foo', 'bar'])[['bar', 'foo']] for ['bar', 'foo'] order. If callable, the callable function will be evaluated against the column names, returning names where the callable function evaluates to True. An example of a valid callable argument would be lambda x: x.upper() in ['AAA', 'BBB', 'DDD'].
                    skiprows (list-like, int or callable, optional): Line numbers to skip (0-indexed) or number of lines to skip (int) at the start of the file. If callable, the callable function will be evaluated against the row indices, returning True if the row should be skipped and False otherwise. An example of a valid callable argument would be lambda x: x in [0, 2].
                    sample_size (int): Number of datapoints to include i.e., number of rows except headers.
                    bool_plot (boolean): If True, will plot the data
            Returns:
                    dataset (numpy.array): a 1-D array
    """
    data_frame = pd.read_csv(dataset, usecols=usecols)
    data = pd.DataFrame.to_numpy(data_frame)
    np.concatenate(data)
    sub_data = data[:sample_size]
    if bool_plot == True:
        plt.figure()
        print("Data Subset: ")
        plt.plot(sub_data)
        plt.show()
    return sub_data


def gradient(data, bool_plot=False):
    """
    Calculates the percent of change of an input dataset.

            Parameters:
                    sub_data (numpy.array): A 1-D array of size N. The sequential data for which the gradient should be calculated.
            Returns:
                    pc numpy.array): A 1-D array of size N. The gradient (percent of change) of the input data. The nth value is the rate of change from xn to xn+1.
    """
    N = len(data)
    pc = np.zeros((N, 1))
    for i in range(N - 1):
        pc[i] = (data[i + 1] - data[i]) / data[i]
    if bool_plot == True:
        plt.figure()
        print("Percent of Change: ")
        plt.scatter(np.linspace(0, N, N), pc, marker=".")
        plt.show()
    return pc


def find_components(
    load_PSD=None,
    signal=None,
    threshold: int = None,
    bool_plot: bool = False,
    save_components: str = None,
):
    """
    Performs a discrete Fourier transform and calculates the modulus squared to estimate the signal's power spectral density.

            Parameters:
                    signal (numpy.array): 1-D data for which the power spectral density is to be estimated.
                    threshold (int): The minimum amplitude squared required for a component frequency to be added to the list of deterministic components.
                    bool_plot (bool) = If True, will show the periodogram.
                    save_components (str, optional) = The name of the file to which the deterministic components will be saved. If not specified, the deterministic components will not be saved.
            Returns:
                    DC (numpy.array): 1-D array containing the frequencies of the component signals with amplitudes above the threshold (the deterministic components).
                    amp (numpy.array): 1-D array containing the amplitudes of the deterministic components. (DC[i] and amp[i] give the frequency and amplitude respectively of a deterministic component signal.)
                    N (int)= Length of the original signal.
    """

    if load_PSD != None:
        PSD = np.load(load_PSD + "components.npy", allow_pickle=True)
        DC = PSD[0]
        amp = PSD[1]
        N = PSD[2]

    else:
        if type(signal) == type(None):
            raise ValueError(
                "'signal' is None: If no file is loaded, a signal and threshold must be given"
            )
        if threshold == None:
            raise ValueError(
                "'threshold' is None: If no file is loaded, a signal and threshold must be specified"
            )
        else:
            # Calculate the power spectral density
            N = len(signal)
            P = np.zeros((N // 2, 1))
            nu = np.zeros((N // 2, 1))
            for k in tqdm(range(N // 2)):
                sum = 0
                for i in range(N):
                    sum += signal[i] * np.exp(2 * np.pi * i * k * 1j * 1 / N)
                P[k] = np.abs(sum) ** 2
                nu[k] = k / N

            if bool_plot == True:
                plt.figure()
                plt.title("Periodogram")
                plt.ylabel("Amplitude squared")
                plt.xlabel("Frequency")
                plt.loglog(nu, P)
                plt.show()

            # This for loop adds all amplitudes above the specified threshold to the list amp and their corresponding frequencies to the list DC.
            amp2 = []
            DC = []
            for i in range(N // 2):
                if P[i] > threshold:
                    amp2.append(P[i])
                    DC.append(nu[i])
            amp = np.sqrt(amp2)
            if save_components != None:
                if not os.path.exists(save_components):
                    os.makedirs(save_components)
                np.save(save_components + "components", np.array([DC, amp, N]))
    return (DC, amp, N)


def build_signal(
    DC,
    amp,
    c_noise: Literal[0, 1, 2, 3, 4],
    trend_type: Literal[0, 1, 2],
    N,
    bool_plot=False,
    labels: str = ["Full Singal", "Day", "Percent of change"],
):
    """
    Constructs a signal from three components: sinusoidal signals, noise, and a long term trend. The sinusoidal signals are given as the parameters DC (a 1-D array of each signal's frequency) and amp (a 1-D array of the corresponding amplitudes)

            Parameters:
                    DC (1-D numpy.array): An array containing the frequencies of the deterministic components.
                    amp (1-D numpy.array): An array containing the amplitudes of the deterministic components.
                    c_noise (0, 1, 2, 3, or 4): Noise coefficient to determine the strength off the noise signal: 0 gives no noise, 4 gives a noise signal for which the maximum signal to noise ratio is 1. The coefficients scale the noise linearly.
                    trend_type (0,1, or 2): 0 -> flat trend: the signal has no long term trend. 1 -> linear trend: the signal has a linear long-term trend with gradient 5e-2. 2 -> quadratic trend: the signal has a quadratic linear trend with gradient 10e-5.
                    N (int)= length of the original signal.
            Returns:
                    full_signal (1-D numpy.array) = The signal consisting of the deterministic (sinusoidal) components, additive noise, and a long term trend.
                    r  (int) = The number of deterministic components. In essence, the length of DC or amp.
    """
    num_components = len(DC)
    interval = (np.linspace(0, N, N)).reshape((N, 1))
    components = np.zeros((N, num_components))
    for i in range(N):
        for j in range(num_components):
            components[i][j] = amp[j] * np.sin(
                DC[j] * interval[i]
            )  # Computing A*sin(omega*x) for each component and x
    DC_signal = np.sum(
        components, axis=-1
    )  # Summing over the components, effectively computing A*sin(omega*x) for each x
    DC_signal = DC_signal.reshape(N, 1)
    c_n = [0, 0.2, 0.5, 0.8, 1]  # 5 possible noise coefficients
    noise_scale = np.abs(np.max(DC_signal) - np.min(DC_signal))
    np.random.seed(0)
    noise = np.random.uniform(0, 1, N) * noise_scale * (c_n[c_noise])
    noise = noise.reshape((N, 1))
    trend = np.array(
        [
            np.zeros(N),
            5e-2 * np.linspace(0, N, N),
            2 * 5e-5 * np.square(np.linspace(0, N, N)),
        ]
    )
    trend = trend.reshape(3, N, 1)

    full_signal = DC_signal + noise + trend[trend_type]
    if bool_plot == True:
        plt.figure()
        plt.title(labels[0])
        plt.xlabel(labels[1])
        plt.ylabel(labels[2])
        plt.plot(range(N), full_signal)
        plt.show()
    r = num_components
    return full_signal, r
