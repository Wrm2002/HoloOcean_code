#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SonarDatasetEmitterActor.generated.h"

class USceneComponent;
class USonarScannerComponent;
class UStaticMeshComponent;

UCLASS(Blueprintable)
class SONARDATASETTOOLS_API ASonarDatasetEmitterActor : public AActor
{
	GENERATED_BODY()

public:
	ASonarDatasetEmitterActor();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Sonar")
	TObjectPtr<USceneComponent> SceneRoot;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Sonar")
	TObjectPtr<USonarScannerComponent> SonarScanner;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Sonar|Visual")
	TObjectPtr<UStaticMeshComponent> VisualMesh;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Path")
	bool bMoveAlongPath = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Path")
	bool bLoopPath = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Path")
	bool bFaceMovementDirection = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Path", meta = (ClampMin = "1.0"))
	float MovementSpeedCmPerSecond = 350.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sonar|Path")
	TArray<FVector> PathPoints;

private:
	int32 CurrentPathTargetIndex = 1;
};
