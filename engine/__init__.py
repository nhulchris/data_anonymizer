"""Data anonymization engine.

Architecture (ICS 499 Team 13):
- detection.py   -- PII detection rules (column names + value patterns)
- mapping.py     -- consistency mapping store, keyed by (pii_type, original value)
- techniques/    -- pluggable anonymization techniques (see techniques/base.py)

Owner: Chris (architecture, mapping, detection config)
Technique implementations: Sophie (substitution, masking, generalization, nulling)
"""
