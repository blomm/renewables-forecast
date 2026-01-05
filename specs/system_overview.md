# System Overview

## Purpose

A renewable energy forecasting system that estimates annual energy generation potential for UK residential solar PV and wind turbine installations based on postcode location.

## Project History

This is a modern rebuild of a system originally created ~20 years ago using UK Met Office data and Google Earth. The new system leverages 2026 AI technology (specifically RAG) while maintaining scientific credibility through deterministic calculations.

## MVP Scope

### Core Promise
"Enter your postcode and system type, get a credible annual energy estimate with an explanation you can interrogate."

### What We Build (MVP)
- Postcode to lat/lon conversion
- Climate data retrieval from public APIs
- Deterministic energy calculations (solar PV and/or wind)
- RAG-based explanation and interrogation system
- Optional user feedback collection for future learning

### What We Don't Build (MVP)
- ❌ Raw weather data ingestion pipelines
- ❌ Custom weather model training
- ❌ Dense local station fusion
- ❌ Real-time updates
- ❌ User telemetry ingestion and processing
- ❌ Microclimate modeling

## Target Users

Primary: UK homeowners considering renewable energy installations
Secondary: Small-scale installers seeking quick feasibility assessments

## Key Design Principles

1. **Scientifically Defensible**: Use established renewable energy assessment formulas
2. **Climate Normals Over History**: Use long-term averages (20-30 year climatology) instead of raw historical time-series
3. **AI for Explanation, Not Prediction**: RAG explains assumptions and contextualizes results; deterministic models make predictions
4. **Gradual Learning**: Collect user feedback for statistical adjustments, not immediate ML retraining
5. **Transparency**: Users can interrogate assumptions and understand the calculation

## Success Metrics

- Annual energy estimate within industry-standard confidence bands (±15-20%)
- Clear, trustworthy explanations of assumptions
- User confidence in making installation decisions
- Foundation for future learning from real-world feedback
