import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Paths
const frontendDir = path.resolve(__dirname, '..');
const openApiPath = path.join(frontendDir, 'src', 'types', 'openapi.json');
const srcDir = path.join(frontendDir, 'src');

if (!fs.existsSync(openApiPath)) {
  console.error(`❌ OpenAPI schema not found at ${openApiPath}`);
  process.exit(1);
}

const openApiData = JSON.parse(fs.readFileSync(openApiPath, 'utf-8'));
const openApiPaths: string[] = Object.keys(openApiData.paths || {});

// Normalize schema paths for regex matching
// E.g., /api/applications/{id}/submit -> ^(?:/api)?/applications/[^/]+/submit$
function pathToRegex(openApiPathStr: string): RegExp {
  const withoutApi = openApiPathStr.startsWith('/api')
    ? openApiPathStr.slice(4)
    : openApiPathStr;

  // Replace {param} with regex for path segment
  const pattern = withoutApi.replace(/\{[^}]+\}/g, '[^/?#]+');
  return new RegExp(`^(?:/api)?${pattern}(?:\\?.*)?$`);
}

const pathRegexes = openApiPaths.map((p) => ({
  original: p,
  regex: pathToRegex(p),
}));

// Recursively find all ts/tsx files in src
function getSourceFiles(dir: string): string[] {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files: string[] = [];

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name !== 'node_modules' && entry.name !== 'dist' && entry.name !== 'types') {
        files.push(...getSourceFiles(fullPath));
      }
    } else if (/\.(ts|tsx)$/.test(entry.name) && !entry.name.endsWith('.d.ts')) {
      files.push(fullPath);
    }
  }

  return files;
}

// Regex to capture api calls:
// api.get('/path' or `...`), api.post(...), api.put(...), api.delete(...)
// and string literals like '/api/alerts/stream'
const apiCallRegex = /(?:api\.(?:get|post|put|patch|delete)<[^>]*>|api\.(?:get|post|put|patch|delete))\s*\(\s*[`'"]([^`'"]+)[`'"]/g;
const apiCallTemplateRegex = /(?:api\.(?:get|post|put|patch|delete)<[^>]*>|api\.(?:get|post|put|patch|delete))\s*\(\s*`([^`]+)`/g;
const streamRegex = /['"](\/api\/[a-zA-Z0-9_\-\/]+)['"]/g;

interface EndpointCall {
  file: string;
  rawPath: string;
  normalizedPath: string;
}

const calls: EndpointCall[] = [];
const sourceFiles = getSourceFiles(srcDir);

for (const file of sourceFiles) {
  const content = fs.readFileSync(file, 'utf-8');

  // Simple literal calls
  let match: RegExpExecArray | null;
  while ((match = apiCallRegex.exec(content)) !== null) {
    const raw = match[1];
    calls.push({
      file: path.relative(frontendDir, file),
      rawPath: raw,
      normalizedPath: raw,
    });
  }

  // Template string calls: `...${id}...`
  while ((match = apiCallTemplateRegex.exec(content)) !== null) {
    const raw = match[1];
    // Replace ${...} with dummy identifier 'sample-id'
    const normalized = raw.replace(/\$\{[^}]+\}/g, 'param-val');
    calls.push({
      file: path.relative(frontendDir, file),
      rawPath: raw,
      normalizedPath: normalized,
    });
  }

  // Special SSE or fetch streams
  while ((match = streamRegex.exec(content)) !== null) {
    const raw = match[1];
    if (raw.startsWith('/api/') && !calls.some((c) => c.rawPath === raw)) {
      calls.push({
        file: path.relative(frontendDir, file),
        rawPath: raw,
        normalizedPath: raw,
      });
    }
  }
}

console.log(`\n🔍 Contract Check: Verifying ${calls.length} frontend API calls against ${openApiPaths.length} OpenAPI routes...`);

let hasError = false;
const checkedCalls = new Set<string>();

for (const call of calls) {
  // Strip query string if any for route matching
  const [basePath] = call.normalizedPath.split('?');
  const cacheKey = `${basePath}`;
  if (checkedCalls.has(cacheKey)) continue;
  checkedCalls.add(cacheKey);

  const isMatched = pathRegexes.some(({ regex }) => regex.test(basePath));

  if (!isMatched) {
    console.error(`❌ Contract violation: [${call.file}] calls unmapped route: "${call.rawPath}" (normalized: "${basePath}")`);
    hasError = true;
  } else {
    console.log(`  ✓ Route verified: "${call.rawPath}"`);
  }
}

if (hasError) {
  console.error('\n❌ Contract check failed! The frontend contains API calls not declared in the OpenAPI schema.\n');
  process.exit(1);
} else {
  console.log('\n✅ Contract check passed! All frontend API calls match OpenAPI schema specifications.\n');
  process.exit(0);
}
