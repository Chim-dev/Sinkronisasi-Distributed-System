from src.consensus.raft import RaftNode
from src.communication.message_passing import MessageBus


def test_request_vote_granted_for_fresh_candidate():
    applied = []
    bus = MessageBus("node1", {"node1": "http://localhost:1", "node2": "http://localhost:2"})
    raft = RaftNode("node1", bus.peers, bus, applied.append)

    response = raft.on_request_vote({"term": 1, "candidate_id": "node2", "last_log_index": -1, "last_log_term": 0})

    assert response["vote_granted"] is True
    assert raft.voted_for == "node2"
