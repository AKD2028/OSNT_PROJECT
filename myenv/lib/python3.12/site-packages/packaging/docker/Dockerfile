# Credits to Jakub Cisek <deex-pl@o2.pl> for creating the original Dockerfile
# available here: https://github.com/cdeex/flent-docker
#
# Can be used for running tests from inside the container
FROM archlinux
RUN pacman -Sy --noconfirm python-pip python-matplotlib netperf fping
RUN pip install flent
RUN mkdir /data
WORKDIR /data

ENTRYPOINT ["/usr/bin/flent"]
CMD ["rrul", "-H", "netperf-eu.bufferbloat.net", "-p", "all_scaled", "-l", "60", "-o", "/data/RRUL_Test.png", "--figure-width=20", "--figure-height=15", "-z"]

