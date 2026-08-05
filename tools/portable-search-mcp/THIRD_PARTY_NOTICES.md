# Third-party notices

Portable Search MCP depends on the `ddgs` Python package and its transitive dependencies. `ddgs` is distributed under the MIT License. Project and license information:

- https://github.com/deedy5/ddgs
- https://github.com/deedy5/ddgs/blob/main/LICENSE.md

The release package installs the exact dependency versions listed in `requirements.lock.txt`. Those projects retain their own copyrights and license terms.

News search may query the public Google News RSS endpoint before falling back to the news providers exposed by `ddgs`. Search terms are sent to those public services; no Google API key or account is used.
