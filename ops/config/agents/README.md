# Agent Configuration

## Overview

This directory contains agent runtime, orchestration, and intent routing configuration for the multi-agent PPM platform. Configuration files define domain agent behavior, the intent router, and response orchestration settings.

## Directory structure

| Folder | Description |
| --- | --- |
| [schema/](./schema/) | JSON schema for intent routing configuration |

## Key files

| File | Description |
| --- | --- |
| [orchestration.yaml](./orchestration.yaml) | Intent router and response orchestration agent settings |
| [intent-routing.yaml](./intent-routing.yaml) | Intent routing rules and agent/action targets per intent |
| [portfolio.yaml](./portfolio.yaml) | Domain agent behavior for demand intake, business case, portfolio strategy, and program management |
| [approval_policies.yaml](./approval_policies.yaml) | Approval workflow escalation and threshold policy including risk/criticality-driven timeouts |
