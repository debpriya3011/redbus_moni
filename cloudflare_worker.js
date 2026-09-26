/**
 * Cloudflare Worker Cron Trigger for RedBus Monitor
 * 
 * This worker runs on a Cloudflare Cron Trigger and dispatches a 
 * GitHub Actions workflow instantly via GitHub's REST API.
 * 
 * Set the following Environment Variables / Secrets in Cloudflare Workers settings:
 *  - GITHUB_OWNER: Your GitHub username or organization (e.g. debpriya3011)
 *  - GITHUB_REPO:  Your repository name (e.g. redbus-monitor)
 *  - GITHUB_PAT:   GitHub Personal Access Token with 'repo' or 'actions:write' permission
 */

export default {
  // Triggered by Cloudflare Cron Schedule (e.g. */5 * * * *)
  async scheduled(event, env, ctx) {
    ctx.waitUntil(triggerGitHubWorkflow(env));
  },

  // Triggered manually by accessing the Worker URL in browser/HTTP client
  async fetch(request, env, ctx) {
    const result = await triggerGitHubWorkflow(env);
    return new Response(JSON.stringify(result, null, 2), {
      headers: { "Content-Type": "application/json" },
      status: result.success ? 200 : 500
    });
  }
};

async function triggerGitHubWorkflow(env) {
  const owner = env.GITHUB_OWNER;
  const repo = env.GITHUB_REPO;
  const token = env.GITHUB_PAT;

  if (!owner || !repo || !token) {
    const err = "Missing required environment variables: GITHUB_OWNER, GITHUB_REPO, or GITHUB_PAT";
    console.error(err);
    return { success: false, error: err };
  }

  const url = `https://api.github.com/repos/${owner}/${repo}/dispatches`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Accept": "application/vnd.github+json",
        "Authorization": `Bearer ${token}`,
        "User-Agent": "Cloudflare-Cron-Worker",
        "X-GitHub-Api-Version": "2022-11-28"
      },
      body: JSON.stringify({
        event_type: "cloudflare-cron"
      })
    });

    if (response.status === 204) {
      console.log(`[SUCCESS] Triggered GitHub workflow dispatch for ${owner}/${repo}`);
      return { success: true, message: `Workflow triggered for ${owner}/${repo}` };
    } else {
      const text = await response.text();
      console.error(`[ERROR] GitHub API returned status ${response.status}: ${text}`);
      return { success: false, status: response.status, error: text };
    }
  } catch (error) {
    console.error(`[EXCEPTION] Failed to send dispatch request: ${error.message}`);
    return { success: false, error: error.message };
  }
}
