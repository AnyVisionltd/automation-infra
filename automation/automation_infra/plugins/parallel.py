from automation_infra.plugins import background


class Parallel(object):

    def __init__(self, run, scripts, base_dir):
        self.run = run
        self.scripts = scripts
        self._base_dir = base_dir
        self.tasks = [background.Background(run, script, Parallel.pidfile(base_dir, i),
                                            Parallel.outfile(base_dir, i),
                                            Parallel.errfile(base_dir, i),
                                            Parallel.statusfile(base_dir, i)) for i, script in enumerate(scripts)]

    @staticmethod
    def pidfile(base_dir, sequence):
        return "%s/%s.pid" % (base_dir, sequence)

    @staticmethod
    def outfile(base_dir, sequence):
        return "%s/%s.out" % (base_dir, sequence)

    @staticmethod
    def errfile(base_dir, sequence):
        return "%s/%s.err" % (base_dir, sequence)

    @staticmethod
    def statusfile(base_dir, sequence):
        return "%s/%s.status" % (base_dir, sequence)


class BackgroundParallel(background.Background, Parallel):

    def __init__(self, run, scripts, base_dir, pid_file, output_file, err_file, status_filename):
        background.Background.__init__(self, run, scripts, pid_file, output_file, err_file, status_filename)
        Parallel.__init__(self, run, scripts, base_dir)
