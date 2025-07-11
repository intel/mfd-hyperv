# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent

out_list_queue = dedent(
    """
 ITEM LIST
===========


  QOS QUEUE: 2
      Friendly name : SQ2
      Enforce intra-host limit: TRUE
      Transmit Limit: 10000
      Transmit Reservation: 0
      Receive Limit: 0
      Transmit Queue Depth: 200 packets
      Receive Queue Depth: 50 packets
      Transmit Burst Size: 50 ms
      Receive Burst Size: 50 ms
      Reservation UnderUtilized watermark: 85%
      Reservation OverUtilized watermark: 95%
      Reservation Headroom: 10%
      Reservation Rampup time: 500 ms
      Reservation Min rate: 10 Mbps

      Current Transmit Info:
        Rate: 10000
        Throttled Packets: 0
        Dropped Packets: 0
      Current Receive Info:
        Rate: DISABLED
        Throttled Packets: 0
        Dropped Packets: 0



  QOS QUEUE: 1
      Friendly name : SQ1
      Enforce intra-host limit: TRUE
      Transmit Limit: 10000
      Transmit Reservation: 0
      Receive Limit: 0
      Transmit Queue Depth: 200 packets
      Receive Queue Depth: 50 packets
      Transmit Burst Size: 50 ms
      Receive Burst Size: 50 ms
      Reservation UnderUtilized watermark: 85%
      Reservation OverUtilized watermark: 95%
      Reservation Headroom: 10%
      Reservation Rampup time: 500 ms
      Reservation Min rate: 10 Mbps

      Current Transmit Info:
        Rate: 10000
        Throttled Packets: 0
        Dropped Packets: 0
      Current Receive Info:
        Rate: DISABLED
        Throttled Packets: 0
        Dropped Packets: 0


Command list-queue succeeded!"""
)

out_get_all_info = dedent(
    """
 ITEM LIST
===========


  QOS QUEUE: 2
      Friendly name : SQ2
      Enforce intra-host limit: TRUE
      Transmit Limit: 10000
      Transmit Reservation: 0
      Receive Limit: 0
      Transmit Queue Depth: 200 packets
      Receive Queue Depth: 50 packets
      Transmit Burst Size: 50 ms
      Receive Burst Size: 50 ms
      Reservation UnderUtilized watermark: 85%
      Reservation OverUtilized watermark: 95%
      Reservation Headroom: 10%
      Reservation Rampup time: 500 ms
      Reservation Min rate: 10 Mbps

      Current Transmit Info:
        Rate: 10000
        Throttled Packets: 0
        Dropped Packets: 0
      Current Receive Info:
        Rate: DISABLED
        Throttled Packets: 0
        Dropped Packets: 0


      Max queue stats since last query:
         Queue Type: Max cap
         Direction: Out
         Elapsed time since last query: 242218580 ms
         Bytes received: 0
         Packets received: 0
         Bytes allowed: 0
         Packets allowed: 0
         Bytes dropped: 0
         Packets dropped: 0
         Bytes delayed due to non-empty queue: 0
         Packets delayed due to non-empty queue: 0
         Bytes delayed due to insufficient tokens: 0
         Packets delayed due to insufficient tokens: 0
         Bytes resumed: 0
         Packets resumed: 0

      Packet events:
         Column 1: Time stamp (100-ns units)
         Column 2: Prerefresh token count
         Column 3: Tokens refreshed
         Column 4: Queue rate (Mbps)
         Column 5: Queue pkt length
         Column 6: Proc number
         Column 7: Bytes received
         Column 8: Packets received
         Column 9: PortId
         Column 10: Queue action

         0: 0: 0: 0: 0: 0: 0: 0: 0: Unknown
         0: 0: 0: 0: 0: 0: 0: 0: 0: Unknown
         0: 0: 0: 0: 0: 0: 0: 0: 0: Unknown

      Resume events:
         Column 1: Time stamp (100-ns units)
         Column 2: Elapsed uSecs since last token refreshed
         Column 3: Proc number
         Column 4: PreRefresh token count
         Column 5: Tokens refreshed
         Column 6: Queue byte length
         Column 7: Queue packet length
         Column 8: Bytes resumed
         Column 9: Packets resumed

         0: 0: 0: 0: 0: 0: 0: 0: 0
         0: 0: 0: 0: 0: 0: 0: 0: 0
         0: 0: 0: 0: 0: 0: 0: 0: 0
         0: 0: 0: 0: 0: 0: 0: 0: 0

  QOS QUEUE: 1
      Friendly name : SQ1
      Enforce intra-host limit: TRUE
      Transmit Limit: 10000
      Transmit Reservation: 0
      Receive Limit: 0
      Transmit Queue Depth: 200 packets
      Receive Queue Depth: 50 packets
      Transmit Burst Size: 50 ms
      Receive Burst Size: 50 ms
      Reservation UnderUtilized watermark: 85%
      Reservation OverUtilized watermark: 95%
      Reservation Headroom: 10%
      Reservation Rampup time: 500 ms
      Reservation Min rate: 10 Mbps

      Current Transmit Info:
        Rate: 10000
        Throttled Packets: 0
        Dropped Packets: 0
      Current Receive Info:
        Rate: DISABLED
        Throttled Packets: 0
        Dropped Packets: 0


      Max queue stats since last query:
         Queue Type: Max cap
         Direction: Out
         Elapsed time since last query: 242218580 ms
         Bytes received: 0
         Packets received: 0
         Bytes allowed: 0
         Packets allowed: 0
         Bytes dropped: 0
         Packets dropped: 0
         Bytes delayed due to non-empty queue: 0
         Packets delayed due to non-empty queue: 0
         Bytes delayed due to insufficient tokens: 0
         Packets delayed due to insufficient tokens: 0
         Bytes resumed: 0
         Packets resumed: 0

      Packet events:
         Column 1: Time stamp (100-ns units)
         Column 2: Prerefresh token count
         Column 3: Tokens refreshed
         Column 4: Queue rate (Mbps)
         Column 5: Queue pkt length
         Column 6: Proc number
         Column 7: Bytes received
         Column 8: Packets received
         Column 9: PortId
         Column 10: Queue action

         0: 0: 0: 0: 0: 0: 0: 0: 0: Unknown
         0: 0: 0: 0: 0: 0: 0: 0: 0: Unknown
         0: 0: 0: 0: 0: 0: 0: 0: 0: Unknown
         0: 0: 0: 0: 0: 0: 0: 0: 0: Unknown
         0: 0: 0: 0: 0: 0: 0: 0: 0: Unknown

      Resume events:
         Column 1: Time stamp (100-ns units)
         Column 2: Elapsed uSecs since last token refreshed
         Column 3: Proc number
         Column 4: PreRefresh token count
         Column 5: Tokens refreshed
         Column 6: Queue byte length
         Column 7: Queue packet length
         Column 8: Bytes resumed
         Column 9: Packets resumed

         0: 0: 0: 0: 0: 0: 0: 0: 0
         0: 0: 0: 0: 0: 0: 0: 0: 0
         0: 0: 0: 0: 0: 0: 0: 0: 0
         0: 0: 0: 0: 0: 0: 0: 0: 0
         0: 0: 0: 0: 0: 0: 0: 0: 0
         0: 0: 0: 0: 0: 0: 0: 0: 0

Command get-queue-info succeeded!"""
)

out_queue_offload = dedent(
    """
 ITEM LIST
===========


  QOS QUEUE: 2
      Friendly name : SQ2
      Enforce intra-host limit: TRUE
      Transmit Limit: 10000
      Transmit Reservation: 0
      Receive Limit: 0
      Transmit Queue Depth: 200 packets
      Receive Queue Depth: 50 packets
      Transmit Burst Size: 50 ms
      Receive Burst Size: 50 ms
      Reservation UnderUtilized watermark: 85%
      Reservation OverUtilized watermark: 95%
      Reservation Headroom: 10%
      Reservation Rampup time: 500 ms
      Reservation Min rate: 10 Mbps

      Current Transmit Info:
        Rate: 10000
        Throttled Packets: 0
        Dropped Packets: 0
      Current Receive Info:
        Rate: DISABLED
        Throttled Packets: 0
        Dropped Packets: 0


      Max queue stats since last query:
         Queue Type: Max cap
         Direction: Out
         Elapsed time since last query: 242218580 ms
         Bytes received: 0
         Packets received: 0
         Bytes allowed: 0
         Packets allowed: 0
         Bytes dropped: 0
         Packets dropped: 0
         Bytes delayed due to non-empty queue: 0
         Packets delayed due to non-empty queue: 0
         Bytes delayed due to insufficient tokens: 0
         Packets delayed due to insufficient tokens: 0
         Bytes resumed: 0
         Packets resumed: 0

    QOS QUEUE: 1
      Friendly name : SQ2
      Enforce intra-host limit: TRUE
      Transmit Limit: 10000
      Transmit Reservation: 0
      Receive Limit: 0
      Transmit Queue Depth: 200 packets
      Receive Queue Depth: 50 packets
      Transmit Burst Size: 50 ms
      Receive Burst Size: 50 ms
      Reservation UnderUtilized watermark: 85%
      Reservation OverUtilized watermark: 95%
      Reservation Headroom: 10%
      Reservation Rampup time: 500 ms
      Reservation Min rate: 10 Mbps

      Current Transmit Info:
        Rate: 10000
        Throttled Packets: 0
        Dropped Packets: 0
      Current Receive Info:
        Rate: DISABLED
        Throttled Packets: 0
        Dropped Packets: 0


      Max queue stats since last query:
         Queue Type: Max cap
         Direction: Out
         Elapsed time since last query: 242218580 ms
         Bytes received: 0
         Packets received: 0
         Bytes allowed: 0
         Packets allowed: 0
         Bytes dropped: 0
         Packets dropped: 0
         Bytes delayed due to non-empty queue: 0
         Packets delayed due to non-empty queue: 0
         Bytes delayed due to insufficient tokens: 0
         Packets delayed due to insufficient tokens: 0
         Bytes resumed: 0
         Packets resumed: 0
         """
)
