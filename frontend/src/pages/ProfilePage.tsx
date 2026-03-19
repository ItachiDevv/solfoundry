import { useState } from "react";
import {
  User,
  Wallet,
  Github,
  Twitter,
  Save,
  Copy,
  CheckCircle,
} from "lucide-react";
import { useAuth } from "../providers/AuthProvider";
import toast from "react-hot-toast";

export function ProfilePage() {
  const { user } = useAuth();

  const [username, setUsername] = useState(user?.username ?? "");
  const [bio, setBio] = useState("");
  const [github, setGithub] = useState("");
  const [twitter, setTwitter] = useState("");
  const [copied, setCopied] = useState(false);

  const walletAddress = user?.walletAddress ?? "Not connected";

  function copyWallet() {
    navigator.clipboard.writeText(walletAddress).then(() => {
      setCopied(true);
      toast.success("Wallet address copied");
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {
      toast.error("Failed to copy");
    });
  }

  function handleSave() {
    // Placeholder - will call authApi.updateProfile
    toast.success("Profile updated (placeholder)");
  }

  return (
    <div className="animate-fade-in max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Profile Settings</h1>
        <p className="text-sm text-foundry-text-muted mt-1">
          Manage your SolFoundry identity
        </p>
      </div>

      {/* Wallet info */}
      <div className="card mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-foundry-purple/10">
            <Wallet size={20} className="text-foundry-purple" />
          </div>
          <div>
            <div className="text-xs text-foundry-text-dim">Connected Wallet</div>
            <div className="font-mono text-sm">{walletAddress}</div>
          </div>
          <button
            onClick={copyWallet}
            className="ml-auto rounded-lg p-2 text-foundry-text-dim hover:bg-foundry-surface hover:text-foundry-text transition-colors"
            title="Copy address"
          >
            {copied ? (
              <CheckCircle size={16} className="text-foundry-green" />
            ) : (
              <Copy size={16} />
            )}
          </button>
        </div>
        <div className="flex gap-4 text-sm">
          <div>
            <span className="text-foundry-text-dim">Role: </span>
            <span className="capitalize font-medium">
              {user?.role ?? "contributor"}
            </span>
          </div>
          <div>
            <span className="text-foundry-text-dim">Reputation: </span>
            <span className="font-bold text-foundry-purple">
              {user?.reputation?.toLocaleString() ?? "0"}
            </span>
          </div>
        </div>
      </div>

      {/* Profile form */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-6">Edit Profile</h2>
        <div className="space-y-5">
          <div>
            <label className="flex items-center gap-2 text-sm font-medium mb-2">
              <User size={14} />
              Display Name
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g., CryptoForge"
              className="input-field w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Bio</label>
            <textarea
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              placeholder="Tell the community about yourself..."
              rows={3}
              className="input-field w-full resize-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="flex items-center gap-2 text-sm font-medium mb-2">
                <Github size={14} />
                GitHub
              </label>
              <input
                type="text"
                value={github}
                onChange={(e) => setGithub(e.target.value)}
                placeholder="username"
                className="input-field w-full"
              />
            </div>
            <div>
              <label className="flex items-center gap-2 text-sm font-medium mb-2">
                <Twitter size={14} />
                Twitter / X
              </label>
              <input
                type="text"
                value={twitter}
                onChange={(e) => setTwitter(e.target.value)}
                placeholder="@handle"
                className="input-field w-full"
              />
            </div>
          </div>
        </div>

        <button
          onClick={handleSave}
          className="btn-primary mt-6 inline-flex items-center gap-2"
        >
          <Save size={14} />
          Save Changes
        </button>
      </div>
    </div>
  );
}
