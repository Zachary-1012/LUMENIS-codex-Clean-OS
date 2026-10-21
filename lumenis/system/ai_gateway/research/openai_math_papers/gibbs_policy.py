"""Trainable instance of OpenAI/math 113 ent:gibbs (finite matching law).

Attribution: OpenAI/math, paper 113, ent:gibbs finite exponential-family equation; source identity is
pinned in lumenis.shared.evaluation.openai_math_papers.provenance.REGISTRY
at upstream fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb.
This bounded Python specialization is not the full paper algorithm or proof.
Upstream paper/source rights remain separate; see LICENSING.md and the
third-party register. This header does not assert a new upstream license grant.


Paper: p_theta(M)=exp(theta·1_M)/Z; grad log Z = edge marginals.
Implementation choice: theta_e = w·features_e. For a supervised matching M*,
grad_w[-log p(M*)] = sum_e (mu_e - 1[e in M*])*features_e.
The gradient is derived from the paper's finite exponential family, not a claim
about OpenAI's undisclosed neural architecture/training recipe.
Decoding enumerates feasible matchings: ALWAYS report constrained/solver-assisted,
never label this inference as tool-free transformer reasoning.
"""

from dataclasses import dataclass
from decimal import Decimal, localcontext

from lumenis.shared.evaluation.openai_math_papers.core import (
    Budget,
    MathInputError,
    decimal,
    rat,
    wire,
)
from lumenis.shared.evaluation.openai_math_papers.matching_113 import Graph, gibbs


@dataclass
class GibbsMatchingPolicy:
    weights: list[Decimal]
    step: int = 0

    def __post_init__(self):
        if type(self.step) is not int or self.step < 0:
            raise MathInputError("POLICY_STEP_INVALID")
        if not 1 <= len(self.weights) <= 32 or any(
            not isinstance(w, Decimal) or not w.is_finite() or abs(w) > 100
            for w in self.weights
        ):
            raise MathInputError("POLICY_WEIGHT_SHAPE")

    def _features(self, graph: Graph, features):
        if not isinstance(features, list) or len(features) != len(graph.edges):
            raise MathInputError("EDGE_FEATURE_SHAPE")
        out = []
        for row in features:
            if not isinstance(row, list) or len(row) != len(self.weights):
                raise MathInputError("FEATURE_WIDTH")
            q = [rat(v) for v in row]
            if any(abs(v) > 10 for v in q):
                raise MathInputError("FEATURE_MAGNITUDE")
            out.append([decimal(v) for v in q])
        return out

    def predict(self, graph: Graph, features, budget: Budget):
        f = self._features(graph, features)
        with localcontext() as c:
            c.prec = 60
            theta = [
                sum((w * x for w, x in zip(self.weights, row)), Decimal(0)) for row in f
            ]
            if any(abs(t) > 1000 for t in theta):
                raise MathInputError("SCORE_RANGE_REQUIRES_RESCALED_FEATURES")
            result = gibbs(graph, [str(v) for v in theta], budget)
            result["learned_edge_scores"] = theta
            result["inference_type"] = (
                "learned scores + exact-support constrained Gibbs inference"
            )
            return result

    def update(self, graph: Graph, features, target, learning_rate, budget: Budget):
        if not graph.check(target):
            raise MathInputError("SUPERVISED_MATCHING_INVALID")
        lr = decimal(learning_rate)
        if not 0 < lr <= 1:
            raise MathInputError("LEARNING_RATE")
        f = self._features(graph, features)
        before = self.predict(graph, features, budget)
        if before["state"] != "COMPUTED":
            raise MathInputError("TRAINING_GRAPH_HAS_NO_MATCHING")
        target = set(target)
        with localcontext() as c:
            c.prec = 60
            mu = before["marginals"]
            grad = [
                sum(
                    (
                        (mu[e] - (1 if e in target else 0)) * f[e][j]
                        for e in range(len(f))
                    ),
                    Decimal(0),
                )
                for j in range(len(self.weights))
            ]
            loss = before["log_partition"] - sum(
                (before["learned_edge_scores"][e] for e in target), Decimal(0)
            )
            proposed = [w - lr * g for w, g in zip(self.weights, grad)]
            if any(not w.is_finite() or abs(w) > 100 for w in proposed):
                raise MathInputError("WEIGHT_UPDATE_OUT_OF_APPROVED_RANGE")
            self.weights = proposed
            self.step += 1
        return {
            "step": self.step,
            "preupdate_nll": loss,
            "gradient": grad,
            "weights": self.weights,
            "paper_equation": "ent:gibbs; derivative d(log Z)/d theta = marginals",
            "not_claimed": "new general-purpose LLM architecture, theorem proof, or established transfer gain",
        }

    def state(self):
        return wire(
            {
                "type": "paper113_finite_matching_exponential_family",
                "weights": self.weights,
                "step": self.step,
                "upstream": "openai/math@fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb",
                "training_recipe": "linear edge features, exact-partition NLL; implementation derivation, not published frontier training",
            }
        )
