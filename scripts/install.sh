. /root/.venv-arrow/bin/activate
supervisorctl stop arrow
pip uninstall arrow --yes
pip install --index-url http://registry.int.exussum.org arrow --trusted-host registry.int.exussum.org
supervisorctl start arrow
tail -f /var/log/arrow.log
