@anthropic-ai/sdk 1.14.0 (https://github.com/anthropics/anthropic-sdk-typescript), Apache 2.0:
see LICENSE. Bundled into one browser ES module, anthropic-sdk.mjs, with the packages it imports
(@opentelemetry/api, standardwebhooks, @stablelib/base64, fast-sha256: see THIRD-PARTY-NOTICES.txt).
interviewer.js loads it on the first AI hint, to call the API with the visitor's own key.

Built with esbuild 0.25.12 from this entry file:

  export {
    Anthropic, APIError, APIConnectionError, APIUserAbortError, AuthenticationError, BadRequestError,
    NotFoundError, PermissionDeniedError, RateLimitError,
  } from "@anthropic-ai/sdk";

  npm install @anthropic-ai/sdk@1.14.0 esbuild@0.25.12
  npx esbuild entry.mjs --bundle --format=esm --platform=browser --minify --legal-comments=eof \
    --outfile=anthropic-sdk.mjs
