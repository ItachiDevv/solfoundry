import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";

type Step = "details" | "reward" | "review";

const steps: { key: Step; label: string }[] = [
  { key: "details", label: "Details" },
  { key: "reward", label: "Reward" },
  { key: "review", label: "Review" },
];

export function CreateBountyPage() {
  const [currentStep, setCurrentStep] = useState<Step>("details");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [difficulty, setDifficulty] = useState("intermediate");
  const [tags, setTags] = useState("");
  const [rewardAmount, setRewardAmount] = useState("");
  const [rewardToken, setRewardToken] = useState("SOL");
  const [deadline, setDeadline] = useState("");

  const currentIndex = steps.findIndex((s) => s.key === currentStep);

  function goNext() {
    if (currentIndex < steps.length - 1) {
      setCurrentStep(steps[currentIndex + 1].key);
    }
  }

  function goBack() {
    if (currentIndex > 0) {
      setCurrentStep(steps[currentIndex - 1].key);
    }
  }

  return (
    <div className="animate-fade-in max-w-2xl">
      <Link
        to="/bounties"
        className="inline-flex items-center gap-2 text-sm text-foundry-text-muted hover:text-foundry-text transition-colors mb-6"
      >
        <ArrowLeft size={16} />
        Back to Bounties
      </Link>

      <h1 className="text-2xl font-bold mb-2">Create a Bounty</h1>
      <p className="text-sm text-foundry-text-muted mb-8">
        Define the work, set the reward, and fund the escrow.
      </p>

      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-8">
        {steps.map((step, i) => {
          const isActive = i === currentIndex;
          const isCompleted = i < currentIndex;
          return (
            <div key={step.key} className="flex items-center gap-2">
              {i > 0 && (
                <div
                  className={`h-px w-8 ${
                    isCompleted ? "bg-foundry-purple" : "bg-foundry-border"
                  }`}
                />
              )}
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition-colors ${
                  isActive
                    ? "bg-foundry-purple text-white"
                    : isCompleted
                      ? "bg-foundry-purple/20 text-foundry-purple"
                      : "bg-foundry-surface text-foundry-text-dim border border-foundry-border"
                }`}
              >
                {isCompleted ? <Check size={14} /> : i + 1}
              </div>
              <span
                className={`text-sm font-medium ${
                  isActive
                    ? "text-foundry-text"
                    : "text-foundry-text-dim"
                }`}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Step content */}
      <div className="card">
        {currentStep === "details" && (
          <div className="space-y-5">
            <div>
              <label className="block text-sm font-medium mb-2">Title</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Implement token staking contract"
                className="input-field w-full"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe the work needed, acceptance criteria, and any relevant links..."
                rows={6}
                className="input-field w-full resize-none"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Difficulty
                </label>
                <select
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                  className="input-field w-full"
                >
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                  <option value="expert">Expert</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Tags</label>
                <input
                  type="text"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder="rust, anchor, defi"
                  className="input-field w-full"
                />
              </div>
            </div>
          </div>
        )}

        {currentStep === "reward" && (
          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Reward Amount
                </label>
                <input
                  type="number"
                  value={rewardAmount}
                  onChange={(e) => setRewardAmount(e.target.value)}
                  placeholder="50"
                  className="input-field w-full"
                  min="0"
                  step="0.1"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Token</label>
                <select
                  value={rewardToken}
                  onChange={(e) => setRewardToken(e.target.value)}
                  className="input-field w-full"
                >
                  <option value="SOL">SOL</option>
                  <option value="USDC">USDC</option>
                  <option value="FORGE">FORGE</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">
                Deadline (optional)
              </label>
              <input
                type="date"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                className="input-field w-full"
              />
            </div>
            <div className="rounded-lg border border-foundry-border bg-foundry-bg p-4">
              <div className="text-xs text-foundry-text-dim mb-2">
                Escrow Info
              </div>
              <p className="text-sm text-foundry-text-muted">
                The reward amount will be transferred to a program-owned escrow
                account upon creation. Funds are released to the contributor
                upon approval or refunded if the bounty is cancelled.
              </p>
            </div>
          </div>
        )}

        {currentStep === "review" && (
          <div className="space-y-4">
            <h3 className="font-semibold mb-4">Review Your Bounty</h3>
            <div className="space-y-3">
              <div className="flex justify-between border-b border-foundry-border pb-3">
                <span className="text-sm text-foundry-text-dim">Title</span>
                <span className="text-sm font-medium">
                  {title || "Not set"}
                </span>
              </div>
              <div className="flex justify-between border-b border-foundry-border pb-3">
                <span className="text-sm text-foundry-text-dim">
                  Difficulty
                </span>
                <span className="text-sm font-medium capitalize">
                  {difficulty}
                </span>
              </div>
              <div className="flex justify-between border-b border-foundry-border pb-3">
                <span className="text-sm text-foundry-text-dim">Reward</span>
                <span className="text-sm font-bold text-foundry-green">
                  {rewardAmount || "0"} {rewardToken}
                </span>
              </div>
              <div className="flex justify-between border-b border-foundry-border pb-3">
                <span className="text-sm text-foundry-text-dim">Tags</span>
                <span className="text-sm">
                  {tags || "None"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-foundry-text-dim">Deadline</span>
                <span className="text-sm">{deadline || "No deadline"}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="mt-6 flex justify-between">
        <button
          onClick={goBack}
          disabled={currentIndex === 0}
          className="btn-secondary inline-flex items-center gap-2"
        >
          <ArrowLeft size={14} />
          Back
        </button>
        {currentStep === "review" ? (
          <button className="btn-success inline-flex items-center gap-2">
            <Check size={14} />
            Create & Fund Escrow
          </button>
        ) : (
          <button
            onClick={goNext}
            className="btn-primary inline-flex items-center gap-2"
          >
            Next
            <ArrowRight size={14} />
          </button>
        )}
      </div>
    </div>
  );
}
