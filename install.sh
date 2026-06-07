. .venv-arrow/bin/activate
supervisorctl stop arrow
pip uninstall arrow --yes
pip install --index-url http://registry.int.exussum.example arrow --trusted-host registry.int.exussum.example
supervisorctl start arrow
tail -f /var/log/arrow.log
