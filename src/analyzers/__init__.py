"""
Java static code analyzer package.
"""
from .java_analyzer import analyze_java_file, analyze_java_source, analyze_java_repository

__all__ = ["analyze_java_file", "analyze_java_source", "analyze_java_repository"]
