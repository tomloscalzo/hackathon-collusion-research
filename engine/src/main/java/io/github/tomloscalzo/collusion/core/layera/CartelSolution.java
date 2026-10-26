package io.github.tomloscalzo.collusion.core.layera;

import java.util.List;

/**
 * Solution of the cartel problem (eq. 12-13). wStar is W at the (refined) thetaStar. screenChangeTreatedAsLevel is
 * true when the scenario screen kind is CHANGE, which the stationary solver treats as LEVEL.
 */
public record CartelSolution(double thetaHat, double thetaStar, double thetaStarGivenParticipation, double wStar,
                             double w0, double ripeness, Regime regime, boolean multipleStageNash,
                             boolean myopicallyUnripe, boolean screenChangeTreatedAsLevel,
                             List<Double> thetaGrid, List<Double> wGrid, List<Boolean> icGrid) {}
