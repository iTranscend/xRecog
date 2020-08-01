import threading
from inspect import signature
from ui.eventemitter import EventEmitter


class Parallelizer(EventEmitter):
    def __init__(self, items, jobs, handler, *, sentinel=None):
        super().__init__()
        try:
            jobs = min(jobs, len(items))
        except:
            pass
        self.__items = iter(items) if not callable(
            items) else iter(items, sentinel)
        self.__itemsLock = threading.Lock()
        self.__takesChecker = len(signature(handler).parameters) == 2
        self.__handler = handler
        self.__threads = []
        self.__doneLock = threading.Lock()
        self.__started = threading.Event()
        self.__finished = threading.Event()
        for job in range(jobs):
            self.__newThread(job)

    def __threadHandler(self, threadEvent, cancelledEvent):
        def newConstraintChecker(listeners):
            def checkConstraint(handle=None, persist=False):
                if handle:
                    if not persist:
                        listeners.append(handle)
                    threadEvent.on('cancel', handle)
                else:
                    return cancelledEvent.isSet()
            return checkConstraint

        try:
            while not cancelledEvent.isSet():
                listeners = []
                try:
                    try:
                        with self.__itemsLock:
                            item = next(self.__items)
                    except StopIteration:
                        break
                    if self.__takesChecker:
                        self.__handler(item, newConstraintChecker(listeners))
                    else:
                        self.__handler(item)
                finally:
                    for listener in listeners:
                        threadEvent.removeListener('cancel', listener)
        finally:
            self.__tickThread()

    def __tickThread(self):
        if not self.hasStarted():
            return
        with self.__doneLock:
            if all(not threadStack["thread"].is_alive() for threadStack in self.__threads if threadStack["thread"] != threading.current_thread()):
                self.__finished.set()
                self.emit('finished')

    def __newThread(self, index):
        threadEvent = EventEmitter()
        cancelledEvent = threading.Event()
        threadEvent.on("cancel", cancelledEvent.set)
        thread = threading.Thread(
            name="ParallelizerThread-%d" % index,
            target=self.__threadHandler,
            args=(threadEvent, cancelledEvent))
        self.__threads.append(
            {"thread": thread, "cancelled": cancelledEvent, "threadEvent": threadEvent})

    def start(self):
        if self.hasStarted():
            raise RuntimeError(
                "Parallelizer instances can only be started once")
        self.__started.set()
        self.emit('started')
        for threadStack in self.__threads:
            threadStack["thread"].start()

    def hasStarted(self):
        return self.__started.isSet()

    def finished(self, n):
        return self.hasStarted() and not self.__threads[n]["thread"].is_alive()

    def allFinished(self):
        return self.__finished.isSet()

    def wait(self, n=None):
        return self.__finished.wait(n)

    def cancelled(self, n):
        return self.__threads[n]["cancelled"].isSet()

    def allCancelled(self):
        return all(threadStack["cancelled"].isSet() for threadStack in self.__threads)

    def cancel(self):
        for threadStack in self.__threads:
            threadStack["threadEvent"].emit("cancel")
        self.emit("cancel")

    def join(self, n):
        return self.__threads[n]["thread"].join()

    def joinAll(self):
        for threadStack in self.__threads:
            threadStack["thread"].join()


if __name__ == "__main__":
    import time

    def test1():
        def executor(item, doCancel):
            thread = threading.current_thread()
            print(" * item %d on %a, init (cancel = %a)" %
                  (item, thread.getName(), doCancel()))
            time.sleep(1)
            print(" * item %d on %a, done (cancel = %a)" %
                  (item, thread.getName(), doCancel()))

        par = Parallelizer(range(10), 4, executor)
        par.on("cancel", lambda: print(" Cancelling jobs"))
        par.on("started", lambda: print(" Started thread execution"))
        par.on("finished", lambda: print(" All threads finished execution"))
        par.start()
        par.cancel()
        par.joinAll()

    def test2():
        import queue
        q = queue.Queue()

        def executor(item, doCancel):
            thread = threading.current_thread()
            print(" * item %02d on %a, init (cancel = %a)" %
                  (item, thread.getName(), doCancel()))
            time.sleep(1)
            print(" * item %02d on %a, done (cancel = %a)" %
                  (item, thread.getName(), doCancel()))

        par = Parallelizer(q.get, 4, executor, sentinel=None)
        par.on("cancel", lambda: print(" Cancelling jobs"))
        par.on("cancel", lambda: q.put(None))
        par.on("started", lambda: print(" Started thread execution"))
        par.on("finished", lambda: print(" All threads finished execution"))
        print("(i) Use ctrl+c to initiate cancel")
        try:
            par.start()
            for item in range(100):
                q.put(item)
            par.joinAll()
        except KeyboardInterrupt:
            par.cancel()

    print("Running test 1")
    test1()
    print()
    print("Running test 2")
    test2()
