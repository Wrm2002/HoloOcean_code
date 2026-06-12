#include "SonarDatasetEmitterActor.h"

#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Kismet/KismetMathLibrary.h"
#include "SonarScannerComponent.h"

ASonarDatasetEmitterActor::ASonarDatasetEmitterActor()
{
	PrimaryActorTick.bCanEverTick = true;

	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	SetRootComponent(SceneRoot);

	VisualMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("VisualMesh"));
	VisualMesh->SetupAttachment(SceneRoot);
	VisualMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	VisualMesh->SetRelativeLocation(FVector::ZeroVector);
	VisualMesh->SetRelativeRotation(FRotator::ZeroRotator);
	VisualMesh->SetRelativeScale3D(FVector(1.0f));

	SonarScanner = CreateDefaultSubobject<USonarScannerComponent>(TEXT("SonarScanner"));
	SonarScanner->TraceLength = 30000.0f;
	SonarScanner->OutputDirectory = TEXT("Saved/SonarDataset_HolodeckSmoke01");
	SonarScanner->bAutoSaveDatasetFrames = true;
	SonarScanner->AutoSaveIntervalSeconds = 0.5f;
	SonarScanner->MaxAutoSaveFrames = 1;
	SonarScanner->bDrawDebug = false;
}

void ASonarDatasetEmitterActor::BeginPlay()
{
	Super::BeginPlay();

	if (PathPoints.Num() > 0)
	{
		SetActorLocation(PathPoints[0]);
		CurrentPathTargetIndex = PathPoints.Num() > 1 ? 1 : 0;
	}
}

void ASonarDatasetEmitterActor::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	if (!bMoveAlongPath || PathPoints.Num() < 2 || MovementSpeedCmPerSecond <= 0.0f)
	{
		return;
	}

	if (!PathPoints.IsValidIndex(CurrentPathTargetIndex))
	{
		if (!bLoopPath)
		{
			return;
		}
		CurrentPathTargetIndex = 0;
	}

	const FVector CurrentLocation = GetActorLocation();
	const FVector TargetLocation = PathPoints[CurrentPathTargetIndex];
	const FVector ToTarget = TargetLocation - CurrentLocation;
	const float DistanceToTarget = ToTarget.Size();
	const float StepDistance = MovementSpeedCmPerSecond * DeltaSeconds;

	if (DistanceToTarget <= FMath::Max(1.0f, StepDistance))
	{
		SetActorLocation(TargetLocation);
		++CurrentPathTargetIndex;
		if (CurrentPathTargetIndex >= PathPoints.Num())
		{
			CurrentPathTargetIndex = bLoopPath ? 0 : PathPoints.Num();
		}
		return;
	}

	const FVector Direction = ToTarget / DistanceToTarget;
	SetActorLocation(CurrentLocation + Direction * StepDistance);

	if (bFaceMovementDirection)
	{
		SetActorRotation(UKismetMathLibrary::MakeRotFromX(Direction));
	}
}
