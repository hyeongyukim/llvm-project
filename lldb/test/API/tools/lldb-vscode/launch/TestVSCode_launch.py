"""
Test lldb-vscode setBreakpoints request
"""


import unittest2
import vscode
from lldbsuite.test.decorators import *
from lldbsuite.test.lldbtest import *
from lldbsuite.test import lldbutil
import lldbvscode_testcase
import time
import os


class TestVSCode_launch(lldbvscode_testcase.VSCodeTestCaseBase):

    mydir = TestBase.compute_mydir(__file__)

    @skipIfWindows
    @skipIfDarwin # Flaky
    @skipIfRemote
    def test_default(self):
        '''
            Tests the default launch of a simple program. No arguments,
            environment, or anything else is specified.
        '''
        program = self.getBuildArtifact("a.out")
        self.build_and_launch(program)
        self.continue_to_exit()
        # Now get the STDOUT and verify our program argument is correct
        output = self.get_stdout()
        self.assertTrue(output and len(output) > 0,
                        "expect program output")
        lines = output.splitlines()
        self.assertIn(program, lines[0],
                      "make sure program path is in first argument")

    @skipIfWindows
    @skipIfRemote
    def test_termination(self):
        '''
            Tests the correct termination of lldb-vscode upon a 'disconnect'
            request.
        '''
        self.create_debug_adaptor()
        # The underlying lldb-vscode process must be alive
        self.assertEqual(self.vscode.process.poll(), None)

        # The lldb-vscode process should finish even though
        # we didn't close the communication socket explicitly
        self.vscode.request_disconnect()

        # Wait until the underlying lldb-vscode process dies.
        # We need to do this because the popen.wait function in python2.7
        # doesn't have a timeout argument.
        for _ in range(10):
            time.sleep(1)
            if self.vscode.process.poll() is not None:
                break
        # Check the return code
        self.assertEqual(self.vscode.process.poll(), 0)

    @skipIfWindows
    @skipIfRemote
    def test_stopOnEntry(self):
        '''
            Tests the default launch of a simple program that stops at the
            entry point instead of continuing.
        '''
        program = self.getBuildArtifact("a.out")
        self.build_and_launch(program, stopOnEntry=True)
        self.set_function_breakpoints(['main'])
        stopped_events = self.continue_to_next_stop()
        for stopped_event in stopped_events:
            if 'body' in stopped_event:
                body = stopped_event['body']
                if 'reason' in body:
                    reason = body['reason']
                    self.assertTrue(
                        reason != 'breakpoint',
                        'verify stop isn\'t "main" breakpoint')

    @skipIfWindows
    @skipIfRemote
    def test_cwd(self):
        '''
            Tests the default launch of a simple program with a current working
            directory.
        '''
        program = self.getBuildArtifact("a.out")
        program_parent_dir = os.path.realpath(
            os.path.dirname(os.path.dirname(program)))
        self.build_and_launch(program,
                              cwd=program_parent_dir)
        self.continue_to_exit()
        # Now get the STDOUT and verify our program argument is correct
        output = self.get_stdout()
        self.assertTrue(output and len(output) > 0,
                        "expect program output")
        lines = output.splitlines()
        found = False
        for line in lines:
            if line.startswith('cwd = \"'):
                quote_path = '"%s"' % (program_parent_dir)
                found = True
                self.assertIn(quote_path, line,
                              "working directory '%s' not in '%s'" % (
                                  program_parent_dir, line))
        self.assertTrue(found, "verified program working directory")

    @skipIfWindows
    @skipIfRemote
    def test_debuggerRoot(self):
        '''
            Tests the "debuggerRoot" will change the working directory of
            the lldb-vscode debug adaptor.
        '''
        program = self.getBuildArtifact("a.out")
        program_parent_dir = os.path.realpath(
            os.path.dirname(os.path.dirname(program)))
        commands = ['platform shell echo cwd = $PWD']
        self.build_and_launch(program,
                              debuggerRoot=program_parent_dir,
                              initCommands=commands)
        output = self.get_console()
        self.assertTrue(output and len(output) > 0,
                        "expect console output")
        lines = output.splitlines()
        prefix = 'cwd = '
        found = False
        for line in lines:
            if line.startswith(prefix):
                found = True
                self.assertEquals(program_parent_dir, line[len(prefix):],
                                "lldb-vscode working dir '%s' == '%s'" % (
                                    program_parent_dir, line[6:]))
        self.assertTrue(found, "verified lldb-vscode working directory")
        self.continue_to_exit()

    @skipIfWindows
    @skipIfRemote
    def test_sourcePath(self):
        '''
            Tests the "sourcePath" will set the target.source-map.
        '''
        program = self.getBuildArtifact("a.out")
        program_dir = os.path.dirname(program)
        self.build_and_launch(program,
                              sourcePath=program_dir)
        output = self.get_console()
        self.assertTrue(output and len(output) > 0,
                        "expect console output")
        lines = output.splitlines()
        prefix = '(lldb) settings set target.source-map "." '
        found = False
        for line in lines:
            if line.startswith(prefix):
                found = True
                quoted_path = '"%s"' % (program_dir)
                self.assertEquals(quoted_path, line[len(prefix):],
                                "lldb-vscode working dir %s == %s" % (
                                    quoted_path, line[6:]))
        self.assertTrue(found, 'found "sourcePath" in console output')
        self.continue_to_exit()

    @skipIfWindows
    @skipIfRemote
    def test_disableSTDIO(self):
        '''
            Tests the default launch of a simple program with STDIO disabled.
        '''
        program = self.getBuildArtifact("a.out")
        self.build_and_launch(program,
                              disableSTDIO=True)
        self.continue_to_exit()
        # Now get the STDOUT and verify our program argument is correct
        output = self.get_stdout()
        self.assertEquals(output, None,
                        "expect no program output")

    @skipIfWindows
    @skipIfLinux # shell argument expansion doesn't seem to work on Linux
    @expectedFailureAll(oslist=["freebsd", "netbsd"],
                        bugnumber="llvm.org/pr48349")
    @skipIfRemote
    def test_shellExpandArguments_enabled(self):
        '''
            Tests the default launch of a simple program with shell expansion
            enabled.
        '''
        program = self.getBuildArtifact("a.out")
        program_dir = os.path.dirname(program)
        glob = os.path.join(program_dir, '*.out')
        self.build_and_launch(program, args=[glob], shellExpandArguments=True)
        self.continue_to_exit()
        # Now get the STDOUT and verify our program argument is correct
        output = self.get_stdout()
        self.assertTrue(output and len(output) > 0,
                        "expect no program output")
        lines = output.splitlines()
        for line in lines:
            quote_path = '"%s"' % (program)
            if line.startswith("arg[1] ="):
                self.assertIn(quote_path, line,
                              'verify "%s" expanded to "%s"' % (
                                  glob, program))

    @skipIfWindows
    @skipIfRemote
    def test_shellExpandArguments_disabled(self):
        '''
            Tests the default launch of a simple program with shell expansion
            disabled.
        '''
        program = self.getBuildArtifact("a.out")
        program_dir = os.path.dirname(program)
        glob = os.path.join(program_dir, '*.out')
        self.build_and_launch(program,
                              args=[glob],
                              shellExpandArguments=False)
        self.continue_to_exit()
        # Now get the STDOUT and verify our program argument is correct
        output = self.get_stdout()
        self.assertTrue(output and len(output) > 0,
                        "expect no program output")
        lines = output.splitlines()
        for line in lines:
            quote_path = '"%s"' % (glob)
            if line.startswith("arg[1] ="):
                self.assertIn(quote_path, line,
                              'verify "%s" stayed to "%s"' % (
                                  glob, glob))

    @skipIfWindows
    @skipIfRemote
    def test_args(self):
        '''
            Tests launch of a simple program with arguments
        '''
        program = self.getBuildArtifact("a.out")
        args = ["one", "with space", "'with single quotes'",
                '"with double quotes"']
        self.build_and_launch(program,
                              args=args)
        self.continue_to_exit()

        # Now get the STDOUT and verify our arguments got passed correctly
        output = self.get_stdout()
        self.assertTrue(output and len(output) > 0,
                        "expect program output")
        lines = output.splitlines()
        # Skip the first argument that contains the program name
        lines.pop(0)
        # Make sure arguments we specified are correct
        for (i, arg) in enumerate(args):
            quoted_arg = '"%s"' % (arg)
            self.assertIn(quoted_arg, lines[i],
                          'arg[%i] "%s" not in "%s"' % (i+1, quoted_arg, lines[i]))

    @skipIfWindows
    @skipIfRemote
    def test_environment(self):
        '''
            Tests launch of a simple program with environment variables
        '''
        program = self.getBuildArtifact("a.out")
        env = ["NO_VALUE", "WITH_VALUE=BAR", "EMPTY_VALUE=",
               "SPACE=Hello World"]
        self.build_and_launch(program,
                              env=env)
        self.continue_to_exit()

        # Now get the STDOUT and verify our arguments got passed correctly
        output = self.get_stdout()
        self.assertTrue(output and len(output) > 0,
                        "expect program output")
        lines = output.splitlines()
        # Skip the all arguments so we have only environment vars left
        while len(lines) and lines[0].startswith("arg["):
            lines.pop(0)
        # Make sure each environment variable in "env" is actually set in the
        # program environment that was printed to STDOUT
        for var in env:
            found = False
            for program_var in lines:
                if var in program_var:
                    found = True
                    break
            self.assertTrue(found,
                            '"%s" must exist in program environment (%s)' % (
                                var, lines))

    @skipIfWindows
    @skipIfRemote
    def test_commands(self):
        '''
            Tests the "initCommands", "preRunCommands", "stopCommands",
            "terminateCommands" and "exitCommands" that can be passed during
            launch.

            "initCommands" are a list of LLDB commands that get executed
            before the targt is created.
            "preRunCommands" are a list of LLDB commands that get executed
            after the target has been created and before the launch.
            "stopCommands" are a list of LLDB commands that get executed each
            time the program stops.
            "exitCommands" are a list of LLDB commands that get executed when
            the process exits
            "terminateCommands" are a list of LLDB commands that get executed when
            the debugger session terminates.
        '''
        program = self.getBuildArtifact("a.out")
        initCommands = ['target list', 'platform list']
        preRunCommands = ['image list a.out', 'image dump sections a.out']
        stopCommands = ['frame variable', 'bt']
        exitCommands = ['expr 2+3', 'expr 3+4']
        terminateCommands = ['expr 4+2']
        self.build_and_launch(program,
                              initCommands=initCommands,
                              preRunCommands=preRunCommands,
                              stopCommands=stopCommands,
                              exitCommands=exitCommands,
                              terminateCommands=terminateCommands)

        # Get output from the console. This should contain both the
        # "initCommands" and the "preRunCommands".
        output = self.get_console()
        # Verify all "initCommands" were found in console output
        self.verify_commands('initCommands', output, initCommands)
        # Verify all "preRunCommands" were found in console output
        self.verify_commands('preRunCommands', output, preRunCommands)

        source = 'main.c'
        first_line = line_number(source, '// breakpoint 1')
        second_line = line_number(source, '// breakpoint 2')
        lines = [first_line, second_line]

        # Set 2 breakpoints so we can verify that "stopCommands" get run as the
        # breakpoints get hit
        breakpoint_ids = self.set_source_breakpoints(source, lines)
        self.assertEquals(len(breakpoint_ids), len(lines),
                        "expect correct number of breakpoints")

        # Continue after launch and hit the first breakpoint.
        # Get output from the console. This should contain both the
        # "stopCommands" that were run after the first breakpoint was hit
        self.continue_to_breakpoints(breakpoint_ids)
        output = self.get_console(timeout=1.0)
        self.verify_commands('stopCommands', output, stopCommands)

        # Continue again and hit the second breakpoint.
        # Get output from the console. This should contain both the
        # "stopCommands" that were run after the second breakpoint was hit
        self.continue_to_breakpoints(breakpoint_ids)
        output = self.get_console(timeout=1.0)
        self.verify_commands('stopCommands', output, stopCommands)

        # Continue until the program exits
        self.continue_to_exit()
        # Get output from the console. This should contain both the
        # "exitCommands" that were run after the second breakpoint was hit
        # and the "terminateCommands" due to the debugging session ending
        output = self.collect_console(duration=1.0)
        self.verify_commands('exitCommands', output, exitCommands)
        self.verify_commands('terminateCommands', output, terminateCommands)

    @skipIfWindows
    @skipIfRemote
    def test_extra_launch_commands(self):
        '''
            Tests the "luanchCommands" with extra launching settings
        '''
        self.build_and_create_debug_adaptor()
        program = self.getBuildArtifact("a.out")

        source = 'main.c'
        first_line = line_number(source, '// breakpoint 1')
        second_line = line_number(source, '// breakpoint 2')
        # Set target binary and 2 breakpoints
        # then we can varify the "launchCommands" get run
        # also we can verify that "stopCommands" get run as the
        # breakpoints get hit
        launchCommands = [
            'target create "%s"' % (program),
            'br s -f main.c -l %d' % first_line,
            'br s -f main.c -l %d' % second_line,
            'process launch --stop-at-entry'
        ]

        initCommands = ['target list', 'platform list']
        preRunCommands = ['image list a.out', 'image dump sections a.out']
        stopCommands = ['frame variable', 'bt']
        exitCommands = ['expr 2+3', 'expr 3+4']
        self.launch(program,
                    initCommands=initCommands,
                    preRunCommands=preRunCommands,
                    stopCommands=stopCommands,
                    exitCommands=exitCommands,
                    launchCommands=launchCommands)

        # Get output from the console. This should contain both the
        # "initCommands" and the "preRunCommands".
        output = self.get_console()
        # Verify all "initCommands" were found in console output
        self.verify_commands('initCommands', output, initCommands)
        # Verify all "preRunCommands" were found in console output
        self.verify_commands('preRunCommands', output, preRunCommands)

        # Verify all "launchCommands" were founc in console output
        # After execution, program should launch
        self.verify_commands('launchCommands', output, launchCommands)
        # Verify the "stopCommands" here
        self.continue_to_next_stop()
        output = self.get_console(timeout=1.0)
        self.verify_commands('stopCommands', output, stopCommands)

        # Continue and hit the second breakpoint.
        # Get output from the console. This should contain both the
        # "stopCommands" that were run after the first breakpoint was hit
        self.continue_to_next_stop()
        output = self.get_console(timeout=1.0)
        self.verify_commands('stopCommands', output, stopCommands)

        # Continue until the program exits
        self.continue_to_exit()
        # Get output from the console. This should contain both the
        # "exitCommands" that were run after the second breakpoint was hit
        output = self.get_console(timeout=1.0)
        self.verify_commands('exitCommands', output, exitCommands)

    @skipIfWindows
    @skipIfNetBSD # Hangs on NetBSD as well
    @skipIfDarwin
    @skipIf(archs=["arm", "aarch64"]) # Example of a flaky run http://lab.llvm.org:8011/builders/lldb-aarch64-ubuntu/builds/5540/steps/test/logs/stdio
    def test_terminate_commands(self):
        '''
            Tests that the "terminateCommands", that can be passed during
            launch, are run when the debugger is disconnected.
        '''
        self.build_and_create_debug_adaptor()
        program = self.getBuildArtifact("a.out")

        terminateCommands = ['expr 4+2']
        self.launch(program=program,
                    terminateCommands=terminateCommands)
        self.get_console()
        # Once it's disconnected the console should contain the
        # "terminateCommands"
        self.vscode.request_disconnect(terminateDebuggee=True)
        output = self.collect_console(duration=1.0)
        self.verify_commands('terminateCommands', output, terminateCommands)


    @skipIfWindows
    @skipIfRemote
    def test_progress_events(self):
        '''
            Tests the progress events to ensure we are receiving them.
        '''
        program = self.getBuildArtifact("a.out")
        self.build_and_launch(program)
        # Set a breakpoint at 'main'. This will cause all of the symbol tables
        # for all modules in LLDB to be parsed and we should get a progress
        # event for each shared library.
        breakpoint_ids = self.set_function_breakpoints(['main'])
        self.continue_to_breakpoints(breakpoint_ids)
        # Make sure we at least got some progress events
        self.assertTrue(len(self.vscode.progress_events) > 0)
        # Track all 'progressStart' events by saving all 'progressId' values.
        progressStart_ids = set()
        # Track all 'progressEnd' events by saving all 'progressId' values.
        progressEnd_ids = set()
        # We will watch for events whose title starts with
        # 'Parsing symbol table for ' and we will save the remainder of the
        # line which will contain the shared library basename. Since we set a
        # breakpoint by name for 'main', we will expect to see progress events
        # for all shared libraries that say that the symbol table is being
        # parsed.
        symtab_progress_shlibs = set()
        # Get a list of modules in the current target so we can verify that
        # we do in fact get a progress event for each shared library.
        target_shlibs = self.vscode.get_modules()

        # Iterate over all progress events and save all start and end IDs, and
        # remember any shared libraries that got symbol table parsing progress
        # events.
        # Sleep for 2 seconds to make sure progress_events gets populated
        time.sleep(2)
        for progress_event in self.vscode.progress_events:
            event_type = progress_event['event']
            if event_type == 'progressStart':
                progressStart_ids.add(progress_event['body']['progressId'])
                title = progress_event['body']['title']
                if title.startswith('Parsing symbol table for '):
                    symtab_progress_shlibs.add(title[25:])
            if event_type == 'progressEnd':
                progressEnd_ids.add(progress_event['body']['progressId'])
        # Make sure for each 'progressStart' event, we got a matching
        # 'progressEnd' event.
        self.assertTrue(progressStart_ids == progressEnd_ids,
                        ('Make sure we got a "progressEnd" for each '
                         '"progressStart" event that we have.'))

        ignored_libraries = {"[vdso]"}

        # Verify we got a symbol table parsing progress event for each shared
        # library in our target.
        for target_shlib_basename in target_shlibs.keys():
            if target_shlib_basename in ignored_libraries:
                continue
            self.assertIn(target_shlib_basename, symtab_progress_shlibs,
                            'Make sure we got a symbol table progress event for "%s"' % (target_shlib_basename))
