import re

def wildcard_to_re(s: str) -> str:
    # ABP wildcard "*" -> ".*"
    # Escape regex special chars except "*" which we convert.
    out = []
    for ch in s:
        if ch == "*":
            out.append(".*")
        elif ch in ".^$+?{}[]\\|()":
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)

def abp_anchor_boundary() -> str:
    # ABP '^' = separator boundary (end of host, or non-alnum/._%-)
    return r"(?:[^A-Za-z0-9_\-.%]|$)"

def abp_rule_to_regex(rule: str) -> str | None:
    rule = rule.strip()
    if not rule or rule.startswith("!"):
        return None
    if len(rule) >= 2 and rule[0] == "/" and rule[-1] == "/":
        body = rule[1:-1]
        return body if body else None
    anchored_start = anchored_end = False
    if rule.startswith("||"):
        core = rule[2:]
        core = core.replace("^", "{ABP_BOUNDARY}")
        core_re = wildcard_to_re(core)
        core_re = core_re.replace("{ABP_BOUNDARY}", abp_anchor_boundary())
        return r"^(?:[^:/?#]+:)?//(?:[^/?#]*\.)?" + core_re + abp_anchor_boundary()
    if rule.startswith("|"):
        anchored_start = True
        rule = rule[1:]
    if rule.endswith("|"):
        anchored_end = True
        rule = rule[:-1]
    rule = rule.replace("^", "{ABP_BOUNDARY}")
    core_re = wildcard_to_re(rule)
    core_re = core_re.replace("{ABP_BOUNDARY}", abp_anchor_boundary())
    if anchored_start and anchored_end:
        return r"^" + core_re + r"$"
    if anchored_start:
        return r"^" + core_re
    if anchored_end:
        return core_re + r"$"
    return core_re

def split_rule_and_options(line: str) -> tuple[str, dict]:
    line = line.strip()
    if "$" not in line:
        return line, {}
    rule, optstr = line.split("$", 1)
    opts = {}
    for raw in optstr.split(","):
        raw = raw.strip()
        if not raw:
            continue
        if "=" in raw:
            k, v = raw.split("=", 1)
            opts[k.strip()] = v.strip()
        else:
            opts[raw] = True
    return rule.strip(), opts

def parse_domain_list(v: str) -> tuple[set[str], set[str]]:
    allow, deny = set(), set()
    for part in v.split("|"):
        part = part.strip()
        if not part:
            continue
        if part.startswith("~"):
            deny.add(part[1:].lower())
        else:
            allow.add(part.lower())
    return allow, deny

def host_matches_domain(host: str, domain: str) -> bool:
    host = host.lower()
    domain = domain.lower()
    return host == domain or host.endswith("." + domain)

def domain_option_allows(first_party_host: str, opts: dict) -> bool:
    dom = opts.get("domain")
    if not dom:
        return True
    allow, deny = parse_domain_list(dom)
    if allow:
        ok = any(host_matches_domain(first_party_host, d) for d in allow)
        if not ok:
            return False
    if deny:
        bad = any(host_matches_domain(first_party_host, d) for d in deny)
        if bad:
            return False
    return True
