from katala_match.domains import coaching, dating, jobs


def test_new_domains_run_on_shared_pipeline_interface():
    domains = [jobs, coaching, dating]

    for domain in domains:
        selected = domain.build_demo_pipeline().run(k=1)
        assert len(selected) == 1
        assert selected[0].metadata["score"]["total"] > 0


def test_required_fields_gate_blocks_domain_candidates():
    selected = jobs.build_demo_pipeline([
        {"id": "bad", "title": "", "skill_match": None},
        {"id": "good", "title": "AI role", "skill_match": 0.8, "remote": True, "culture": 0.7},
    ]).run(k=2)

    assert [candidate.id for candidate in selected] == ["good"]
