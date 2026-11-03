import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import gemini_qa_gate as g

GOOD = {"approved": True, "overall_score": 8.8, "hook_strength_0_to_3s": 9.0, "visual_bugs": [], "audio_issues": [],
        "parameter_overrides_for_retry": {"pacing_multiplier": 1.0, "text_y_offset_px": 0, "visual_theme_seed": "default"},
        "code_patch_instructions": ""}


class F:  # fake file
    name, uri, mime_type = "files/x", "uri://x", "video/mp4"
    class state: name = "ACTIVE"


class FakeClient:
    def __init__(self, replies):
        self.replies, self.cfgs = list(replies), []
        c = self
        class Files:
            def upload(s, file): return F()
            def get(s, name): return F()
            def delete(s, name): pass
        class Models:
            def generate_content(s, model, contents, config):
                c.cfgs.append((model, config))
                class R: text = c.replies.pop(0)
                return R()
        self.files, self.models = Files(), Models()


def vid():
    p = tempfile.mktemp(suffix=".mp4"); open(p, "wb").write(b"x"); return p


def test_parse_ok_and_fences():
    assert g.parse_verdict("```json\n" + json.dumps(GOOD) + "\n```").passed


def test_score_rule_overrides_model_claim():
    d = dict(GOOD, overall_score=7.9)
    assert not g.parse_verdict(json.dumps(d)).passed


def test_bad_json_and_types_fail_closed():
    for bad in ["nope", "{}", json.dumps(dict(GOOD, approved="yes")), json.dumps(dict(GOOD, overall_score=11))]:
        try: g.parse_verdict(bad); assert False, bad
        except g.GateError: pass


def test_overrides_clamped():
    o = g.safe_overrides({"pacing_multiplier": 9, "text_y_offset_px": -999, "visual_theme_seed": "a b;rm", "evil": 1})
    assert o == {"pacing_multiplier": 1.5, "text_y_offset_px": -400.0}


def test_config_medium_then_high_no_sampling():
    bad = dict(GOOD, approved=False, overall_score=6, parameter_overrides_for_retry={"pacing_multiplier": 1.2})
    fc = FakeClient([json.dumps(bad), json.dumps(GOOD)])
    calls = []
    def render(ov): calls.append(ov); return vid()
    path, v, hist = g.gate_with_retries(render, client=fc)
    assert v.passed and len(hist) == 2 and calls == [{}, {"pacing_multiplier": 1.2}]
    lv = [c[1].thinking_config.thinking_level.value for c in fc.cfgs]
    assert lv == ["MEDIUM", "HIGH"], lv
    for _, cfg in fc.cfgs:
        assert cfg.max_output_tokens == 65536 and cfg.temperature is None and cfg.top_p is None and cfg.top_k is None
    assert fc.cfgs[0][0] == "gemini-4-argon"


def test_never_passes_returns_last():
    bad = json.dumps(dict(GOOD, approved=False, overall_score=5))
    fc = FakeClient([bad] * 3)
    _, v, hist = g.gate_with_retries(lambda ov: vid(), client=fc)
    assert not v.passed and len(hist) == 3


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f(); print("ok", n)
