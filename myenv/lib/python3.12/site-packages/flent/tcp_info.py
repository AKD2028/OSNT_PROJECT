# -*- coding: utf-8 -*-
#
# tcp_info.py
#
# Author:   Toke Høiland-Jørgensen (toke@toke.dk)
# Date:      6 February 2022
# Copyright (c), 2022, Toke Høiland-Jørgensen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option), any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import ctypes
import sys
import subprocess
import json
import pprint
import enum
import base64

from enum import auto

class InetDiagAttrs(enum.IntEnum):

    #INET_DIAG_NONE = auto()
    INET_DIAG_MEMINFO = auto()
    INET_DIAG_INFO = auto()
    INET_DIAG_VEGASINFO = auto()
    INET_DIAG_CONG = auto()
    INET_DIAG_TOS = auto()
    INET_DIAG_TCLASS = auto()
    INET_DIAG_SKMEMINFO = auto()
    INET_DIAG_SHUTDOWN = auto()

    INET_DIAG_DCTCPINFO = auto()
    INET_DIAG_PROTOCOL = auto()
    INET_DIAG_SKV6ONLY = auto()
    INET_DIAG_LOCALS = auto()
    INET_DIAG_PEERS = auto()
    INET_DIAG_PAD = auto()
    INET_DIAG_MARK = auto()
    INET_DIAG_BBRINFO = auto()
    INET_DIAG_CLASS_ID = auto()
    INET_DIAG_MD5SIG = auto()
    INET_DIAG_ULP_INFO = auto()
    INET_DIAG_SK_BPF_STORAGES = auto()
    INET_DIAG_CGROUP_ID = auto()
    INET_DIAG_SOCKOPT = auto()


# struct tcpvegas_info {
# 	__u32	tcpv_enabled;
# 	__u32	tcpv_rttcnt;
# 	__u32	tcpv_rtt;
# 	__u32	tcpv_minrtt;
# };
#
# /* INET_DIAG_DCTCPINFO */
#
# struct tcp_dctcp_info {
# 	__u16	dctcp_enabled;
# 	__u16	dctcp_ce_state;
# 	__u32	dctcp_alpha;
# 	__u32	dctcp_ab_ecn;
# 	__u32	dctcp_ab_tot;
# };
#
# /* INET_DIAG_BBRINFO */
#
# struct tcp_bbr_info {
# 	/* u64 bw: max-filtered BW (app throughput) estimate in Byte per sec: */
# 	__u32	bbr_bw_lo;		/* lower 32 bits of bw */
# 	__u32	bbr_bw_hi;		/* upper 32 bits of bw */
# 	__u32	bbr_min_rtt;		/* min-filtered RTT in uSec */
# 	__u32	bbr_pacing_gain;	/* pacing gain shifted left 8 bits */
# 	__u32	bbr_cwnd_gain;		/* cwnd gain shifted left 8 bits */
# };


class TcpInfo(ctypes.Structure):
    __u8 = ctypes.c_uint8
    __u32 = ctypes.c_uint32
    __u64 = ctypes.c_uint64
    _fields_ = [
        ("tcpi_state", __u8),
        ("tcpi_ca_state", __u8),
        ("tcpi_retransmits", __u8),
        ("tcpi_probes", __u8),
        ("tcpi_backoff", __u8),
        ("tcpi_options", __u8),
        ("tcpi_snd_wscale", __u8, 4),
        ("tcpi_snd_wscale", __u8, 4),
        ("tcpi_delivery_rate_app_limited", __u8, 1),
        ("tcpi_fastopen_client_fail", __u8, 2),
        ("tcpi_rto", __u32),
        ("tcpi_ato", __u32),
        ("tcpi_snd_mss", __u32),
        ("tcpi_rcv_mss", __u32),
        ("tcpi_unacked", __u32),
        ("tcpi_sacked", __u32),
        ("tcpi_lost", __u32),
        ("tcpi_retrans", __u32),
        ("tcpi_fackets", __u32),
        ("tcpi_last_data_sent", __u32),
        ("tcpi_last_ack_sent", __u32),
        ("tcpi_last_data_recv", __u32),
        ("tcpi_last_ack_recv", __u32),
        ("tcpi_pmtu", __u32),
        ("tcpi_rcv_ssthresh", __u32),
        ("tcpi_rtt", __u32),
        ("tcpi_rttvar", __u32),
        ("tcpi_snd_ssthresh", __u32),
        ("tcpi_snd_cwnd", __u32),
        ("tcpi_advmss", __u32),
        ("tcpi_reordering", __u32),
        ("tcpi_rcv_rtt", __u32),
        ("tcpi_rcv_space", __u32),
        ("tcpi_total_retrans", __u32),
        ("tcpi_pacing_rate", __u64),
        ("tcpi_max_pacing_rate", __u64),
        ("tcpi_bytes_acked", __u64),
        ("tcpi_bytes_received", __u64),
        ("tcpi_segs_out", __u32),
        ("tcpi_segs_in", __u32),
        ("tcpi_notsent_bytes", __u32),
        ("tcpi_min_rtt", __u32),
        ("tcpi_data_segs_in", __u32),
        ("tcpi_data_segs_out", __u32),
        ("tcpi_delivery_rate", __u64),
        ("tcpi_busy_time", __u64),
        ("tcpi_rwnd_limited", __u64),
        ("tcpi_sndbuf_limited", __u64),
        ("tcpi_delivered", __u32),
        ("tcpi_delivered_ce", __u32),
        ("tcpi_bytes_sent", __u64),
        ("tcpi_bytes_retrans", __u64),
        ("tcpi_dsack_dups", __u32),
        ("tcpi_reord_seen", __u32),
        ("tcpi_rcv_ooopack", __u32),
        ("tcpi_snd_wnd", __u32),
    ]

def read_zstd_file(filename):
    proc = subprocess.run(["zstdcat", filename], encoding='ascii',
                          capture_output=True, check=True)
    output = []
    for line in proc.stdout.splitlines():
        output.append(json.loads(line))
    return output

def parse_data(data):
    tcpi = base64.b64decode(data[-1]['Attributes'][InetDiagAttrs['INET_DIAG_INFO']])
    return TcpInfo.from_buffer_copy(tcpi.ljust(ctypes.sizeof(TcpInfo)))


def read_tcpinfo_csv(filename):
    data = read_zstd_file(filename)
    tcpi = parse_data(data)
    for v in TcpInfo._fields_:
        print(v[0], getattr(tcpi,v[0]))
    return tcpi

if __name__ == "__main__":
    print()
    pprint.pprint(read_tcpinfo_csv(sys.argv[1]))
