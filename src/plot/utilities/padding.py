def pad(lst, length):
    '''
    Pads a list with NaN values to ensure it has a specified length.

    Inputs
    -------
        lst: The original list to be padded.
        length: The desired length of the list after padding.

    Returns
    -------
        A new list that contains the original elements of lst followed by enough NaN values to reach
        the specified length.

    Author
    ------
        Claude Opus 4.6
    '''
    return lst + [float('nan')] * (length - len(lst))