import time


def calculate_time(func):
    def inner(*args, **kwargs):
        b = time.time()
        r = func(*args, **kwargs)
        e = time.time()
        print("Time taken to run '{}': {} seconds".format(
            func.__name__, round((e - b), 3)))
        return r
    return inner


def main():
    calculate_time(sum)(range(10000))

    @calculate_time
    def bla(x):
        sum(x)

    bla(range(100))


if __name__ == "__main__":
    main()
