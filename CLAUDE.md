# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Project name: disk-watcher - appears to be a file system monitoring/disk monitoring utility.

## Commands

Build: `go build ./...`
Test: `go test ./...`
Run single test: `go test -v -run TestName ./...`
Lint: `golangci-lint run`

## Architecture

This appears to be a Go project for monitoring disk/file system events. The typical structure is:
- Main entry point in `cmd/` or root
- Core logic in `internal/` or `pkg/`
- Event handling for file system changes
