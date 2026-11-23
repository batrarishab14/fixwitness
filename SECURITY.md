# Security

fixwitness executes the scripts you give it. It runs each one in a fresh temporary directory
with a minimal environment and a timeout, and it never uses a shell to build the command line.
That is process isolation, not a sandbox: the scripts run as your user.

- Run fixwitness inside a container or a CI runner when the scripts are not trusted.
- The built-in attack payloads only try to create an empty marker file in the temporary directory.
- The MCP server refuses programs outside the built-in allow-list (python, bash, sh, node, ...).

To report a vulnerability in fixwitness itself, open a GitHub security advisory on this repository.
