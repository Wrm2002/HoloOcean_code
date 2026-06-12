#include "SonarDatasetBlueprintLibrary.h"
#include "GameFramework/Actor.h"

namespace
{
int32 ResolveClassIdForActor(const AActor* Actor, int32 DefaultClassId)
{
	if (!IsValid(Actor))
	{
		return DefaultClassId;
	}

	for (const FName& TagName : Actor->Tags)
	{
		FString Tag = TagName.ToString().ToLower();
		Tag.TrimStartAndEndInline();

		FString Value;
		if (Tag.Split(TEXT("class_"), nullptr, &Value) ||
			Tag.Split(TEXT("class="), nullptr, &Value) ||
			Tag.Split(TEXT("class:"), nullptr, &Value) ||
			Tag.Split(TEXT("yolo_"), nullptr, &Value) ||
			Tag.Split(TEXT("yolo="), nullptr, &Value) ||
			Tag.Split(TEXT("yolo:"), nullptr, &Value))
		{
			if (!Value.IsEmpty() && Value.IsNumeric())
			{
				return FCString::Atoi(*Value);
			}
		}
	}

	return DefaultClassId;
}
}

FVector2D USonarDatasetBlueprintLibrary::LocalPointToSonarPixel(
	FVector LocalPoint,
	float TraceLength,
	float OriginX,
	float OriginY,
	float DrawRadius,
	bool bClampToImage,
	float ImageWidth,
	float ImageHeight)
{
	if (TraceLength <= KINDA_SMALL_NUMBER)
	{
		return FVector2D(OriginX, OriginY);
	}

	const float PixelX = OriginX + (LocalPoint.Y / TraceLength) * DrawRadius;
	const float PixelY = OriginY - (LocalPoint.X / TraceLength) * DrawRadius;

	if (!bClampToImage)
	{
		return FVector2D(PixelX, PixelY);
	}

	return FVector2D(
		FMath::Clamp(PixelX, 0.0f, ImageWidth),
		FMath::Clamp(PixelY, 0.0f, ImageHeight));
}

bool USonarDatasetBlueprintLibrary::WorldPointToSonarPixel(
	AActor* ReferenceActor,
	FVector WorldPoint,
	float TraceLength,
	FVector& LocalPoint,
	FVector2D& PixelPoint,
	float OriginX,
	float OriginY,
	float DrawRadius,
	bool bClampToImage,
	float ImageWidth,
	float ImageHeight)
{
	if (!IsValid(ReferenceActor))
	{
		LocalPoint = FVector::ZeroVector;
		PixelPoint = FVector2D::ZeroVector;
		return false;
	}

	LocalPoint = ReferenceActor->GetActorTransform().InverseTransformPosition(WorldPoint);
	PixelPoint = LocalPointToSonarPixel(LocalPoint, TraceLength, OriginX, OriginY, DrawRadius, bClampToImage, ImageWidth, ImageHeight);
	return true;
}

void USonarDatasetBlueprintLibrary::BuildSonarPointsFromHits(
	AActor* ReferenceActor,
	const TArray<FVector>& WorldHitPoints,
	float TraceLength,
	TArray<FVector>& LocalPoints,
	TArray<FVector2D>& PixelPoints,
	float OriginX,
	float OriginY,
	float DrawRadius,
	bool bClampToImage,
	float ImageWidth,
	float ImageHeight)
{
	LocalPoints.Reset(WorldHitPoints.Num());
	PixelPoints.Reset(WorldHitPoints.Num());

	if (!IsValid(ReferenceActor))
	{
		return;
	}

	const FTransform ActorTransform = ReferenceActor->GetActorTransform();
	for (const FVector& WorldPoint : WorldHitPoints)
	{
		const FVector LocalPoint = ActorTransform.InverseTransformPosition(WorldPoint);
		LocalPoints.Add(LocalPoint);
		PixelPoints.Add(LocalPointToSonarPixel(LocalPoint, TraceLength, OriginX, OriginY, DrawRadius, bClampToImage, ImageWidth, ImageHeight));
	}
}

void USonarDatasetBlueprintLibrary::BuildYoloBoxesFromSonarPixels(
	const TArray<FVector2D>& PixelPoints,
	const TArray<AActor*>& HitActors,
	float ImageWidth,
	float ImageHeight,
	int32 DefaultClassId,
	TArray<FSonarYoloBox>& Boxes,
	FString& YoloText)
{
	Boxes.Reset();
	YoloText.Reset();

	if (PixelPoints.Num() == 0 || PixelPoints.Num() != HitActors.Num() || ImageWidth <= 0.0f || ImageHeight <= 0.0f)
	{
		return;
	}

	TMap<TObjectPtr<AActor>, int32> ActorToBoxIndex;

	for (int32 Index = 0; Index < PixelPoints.Num(); ++Index)
	{
		AActor* Actor = HitActors[Index];
		if (!IsValid(Actor))
		{
			continue;
		}

		const FVector2D Pixel = PixelPoints[Index];
		int32* ExistingIndex = ActorToBoxIndex.Find(Actor);

		if (!ExistingIndex)
		{
			FSonarYoloBox Box;
			Box.Actor = Actor;
			Box.ActorName = Actor->GetName();
			Box.ClassId = ResolveClassIdForActor(Actor, DefaultClassId);
			Box.MinPixel = Pixel;
			Box.MaxPixel = Pixel;
			ActorToBoxIndex.Add(Actor, Boxes.Add(Box));
			continue;
		}

		FSonarYoloBox& Box = Boxes[*ExistingIndex];
		Box.MinPixel.X = FMath::Min(Box.MinPixel.X, Pixel.X);
		Box.MinPixel.Y = FMath::Min(Box.MinPixel.Y, Pixel.Y);
		Box.MaxPixel.X = FMath::Max(Box.MaxPixel.X, Pixel.X);
		Box.MaxPixel.Y = FMath::Max(Box.MaxPixel.Y, Pixel.Y);
	}

	for (FSonarYoloBox& Box : Boxes)
	{
		constexpr float MinBoxSizePixels = 2.0f;

		Box.CenterPixel = (Box.MinPixel + Box.MaxPixel) * 0.5f;
		Box.SizePixel = Box.MaxPixel - Box.MinPixel;

		if (Box.SizePixel.X < MinBoxSizePixels)
		{
			Box.SizePixel.X = MinBoxSizePixels;
		}
		if (Box.SizePixel.Y < MinBoxSizePixels)
		{
			Box.SizePixel.Y = MinBoxSizePixels;
		}

		const FVector2D HalfSize = Box.SizePixel * 0.5f;
		Box.MinPixel = FVector2D(
			FMath::Clamp(Box.CenterPixel.X - HalfSize.X, 0.0f, ImageWidth),
			FMath::Clamp(Box.CenterPixel.Y - HalfSize.Y, 0.0f, ImageHeight));
		Box.MaxPixel = FVector2D(
			FMath::Clamp(Box.CenterPixel.X + HalfSize.X, 0.0f, ImageWidth),
			FMath::Clamp(Box.CenterPixel.Y + HalfSize.Y, 0.0f, ImageHeight));
		Box.CenterPixel = (Box.MinPixel + Box.MaxPixel) * 0.5f;
		Box.SizePixel = Box.MaxPixel - Box.MinPixel;

		Box.CenterNormalized = FVector2D(Box.CenterPixel.X / ImageWidth, Box.CenterPixel.Y / ImageHeight);
		Box.SizeNormalized = FVector2D(Box.SizePixel.X / ImageWidth, Box.SizePixel.Y / ImageHeight);

		Box.YoloLine = FString::Printf(
			TEXT("%d %.6f %.6f %.6f %.6f"),
			Box.ClassId,
			Box.CenterNormalized.X,
			Box.CenterNormalized.Y,
			Box.SizeNormalized.X,
			Box.SizeNormalized.Y);

		if (!YoloText.IsEmpty())
		{
			YoloText += LINE_TERMINATOR;
		}
		YoloText += Box.YoloLine;
	}
}
