sshpass -p 's@AXuwr7' sftp -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa  giddensm@165.127.62.8 << !
mget /usr/local/cim/bic_etl/general/logs/* logs
!